"""
ocr_engine.py
-------------
Core OCR engine: wraps PaddleOCR 3.x, pre-processes images,
runs inference, post-processes results, and returns structured responses.

Design decisions
----------------
* PaddleOCR is initialised ONCE at construction time and reused for all images.
* enable_mkldnn=False forces run_mode='paddle' on CPU, bypassing the
  PIR + oneDNN NotImplementedError in PaddlePaddle 3.3.1 on Windows.
* The engine accepts both file paths and pre-loaded BGR NumPy arrays.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional, Union

import cv2
import numpy as np

from ocr_module.config import (
    ENABLE_MKLDNN,
    OCR_LANG,
    TEXT_DET_BOX_THRESH,
    TEXT_DET_LIMIT_SIDE_LEN,
    TEXT_DET_LIMIT_TYPE,
    TEXT_DET_THRESH,
    TEXT_DET_UNCLIP_RATIO,
    TEXT_REC_SCORE_THRESH,
    USE_DOC_ORIENTATION_CLASSIFY,
    USE_DOC_UNWARPING,
    USE_TEXTLINE_ORIENTATION,
    MIN_CONFIDENCE,
    ANNOTATED_IMAGE_SUFFIX,
    JSON_SUFFIX,
    SAMPLES_OUTPUT_DIR,
)
from ocr_module.image_utils import draw_ocr_results, save_annotated_image
from ocr_module.models import OCRResponse, OCRTextResult
from ocr_module.postprocessing import postprocess
from ocr_module.preprocessing import preprocess_image

logger = logging.getLogger(__name__)


class OCREngine:
    """
    Singleton-style OCR engine built on PaddleOCR 3.x (PP-OCRv6).

    Usage
    -----
    engine = OCREngine()
    response = engine.process_image("path/to/image.jpg")
    print(response.full_text)
    print(response.model_dump_json(indent=2))
    """

    def __init__(
        self,
        min_confidence: float = MIN_CONFIDENCE,
        enable_preprocessing: bool = True,
        output_dir: Optional[Path] = None,
    ) -> None:
        """
        Parameters
        ----------
        min_confidence      : minimum confidence score to keep a result
        enable_preprocessing: run the image preprocessing pipeline
        output_dir          : where to save JSON + annotated images
                              (defaults to samples/output)
        """
        self.min_confidence       = min_confidence
        self.enable_preprocessing = enable_preprocessing
        self.output_dir           = Path(output_dir) if output_dir else SAMPLES_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Initialising PaddleOCR engine (PP-OCRv6, lang=%s, mkldnn=%s)",
                    OCR_LANG, ENABLE_MKLDNN)
        self._ocr = self._build_ocr()
        logger.info("PaddleOCR engine ready.")

    # ------------------------------------------------------------------
    # Private: build the PaddleOCR object
    # ------------------------------------------------------------------

    @staticmethod
    def _build_ocr():
        """Create and return a PaddleOCR instance with correct CPU settings."""
        from paddleocr import PaddleOCR

        return PaddleOCR(
            lang=OCR_LANG,
            use_doc_orientation_classify=USE_DOC_ORIENTATION_CLASSIFY,
            use_doc_unwarping=USE_DOC_UNWARPING,
            use_textline_orientation=USE_TEXTLINE_ORIENTATION,
            enable_mkldnn=ENABLE_MKLDNN,            # <-- critical fix
            text_det_thresh=TEXT_DET_THRESH,
            text_det_box_thresh=TEXT_DET_BOX_THRESH,
            text_det_unclip_ratio=TEXT_DET_UNCLIP_RATIO,
            text_det_limit_side_len=TEXT_DET_LIMIT_SIDE_LEN,
            text_det_limit_type=TEXT_DET_LIMIT_TYPE,
            text_rec_score_thresh=TEXT_REC_SCORE_THRESH,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_image_array(
        self,
        img: np.ndarray,
        image_name: str = "frame",
        save_outputs: bool = False,
    ) -> OCRResponse:
        """
        Run the full OCR pipeline on a pre-loaded BGR NumPy array.

        Parameters
        ----------
        img          : BGR uint8 numpy array (from cv2.imread or video frame)
        image_name   : label for the response (default: 'frame')
        save_outputs : if True, write JSON + annotated image to output_dir

        Returns
        -------
        OCRResponse pydantic model
        """
        t0 = time.perf_counter()
        try:
            raw_results = self._run_inference(img)
            results, full_text = postprocess(
                raw_results["rec_texts"],
                raw_results["rec_scores"],
                raw_results["rec_polys"],
                min_confidence=self.min_confidence,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            response = OCRResponse(
                success=True,
                image_name=image_name,
                extracted_text=results,
                full_text=full_text,
                processing_time_ms=round(elapsed_ms, 2),
                preprocessing_meta={"steps_applied": ["array_input"]},
            )
            if save_outputs:
                self._save_outputs(img, results, response, image_name)
            logger.info("Array OCR: %d regions, %.1f ms", len(results), elapsed_ms)
            return response
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("Array OCR failed: %s", exc, exc_info=True)
            return OCRResponse(
                success=False,
                image_name=image_name,
                processing_time_ms=round(elapsed_ms, 2),
                error=str(exc),
            )

    def process_image(
        self,
        image_path: Union[str, Path],
        save_outputs: bool = True,
    ) -> OCRResponse:
        """
        Run the full OCR pipeline on a single image file.

        Parameters
        ----------
        image_path   : path to the input image (JPG / PNG / BMP)
        save_outputs : if True, write JSON + annotated image to output_dir

        Returns
        -------
        OCRResponse pydantic model
        """
        image_path = Path(image_path)
        image_name = image_path.name
        t0 = time.perf_counter()

        try:
            # Stage 1 & 2: load + preprocess
            if self.enable_preprocessing:
                img, pre_meta = preprocess_image(image_path)
            else:
                img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
                if img is None:
                    raise IOError(f"Cannot read image: {image_path}")
                pre_meta = {"steps_applied": ["load_only"]}

            # Stage 3 & 4: detect + recognise
            raw_results = self._run_inference(img)

            # Stage 5: post-process
            results, full_text = postprocess(
                raw_results["rec_texts"],
                raw_results["rec_scores"],
                raw_results["rec_polys"],
                min_confidence=self.min_confidence,
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            response = OCRResponse(
                success=True,
                image_name=image_name,
                extracted_text=results,
                full_text=full_text,
                processing_time_ms=round(elapsed_ms, 2),
                preprocessing_meta=pre_meta,
            )

            # Stage 6: save outputs
            if save_outputs:
                self._save_outputs(img, results, response, image_path.stem)

            logger.info("Processed %s: %d text regions, %.1f ms",
                        image_name, len(results), elapsed_ms)
            return response

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("Failed to process %s: %s", image_name, exc, exc_info=True)
            return OCRResponse(
                success=False,
                image_name=image_name,
                processing_time_ms=round(elapsed_ms, 2),
                error=str(exc),
            )

    def process_batch(
        self,
        image_paths: List[Union[str, Path]],
        save_outputs: bool = True,
    ) -> List[OCRResponse]:
        """
        Process a list of image files and return a list of OCRResponse objects.

        Parameters
        ----------
        image_paths  : list of image file paths
        save_outputs : save JSON + annotated images for each image

        Returns
        -------
        list of OCRResponse objects (one per input image)
        """
        responses = []
        total = len(image_paths)
        for idx, path in enumerate(image_paths, 1):
            logger.info("[%d/%d] Processing: %s", idx, total, Path(path).name)
            response = self.process_image(path, save_outputs=save_outputs)
            responses.append(response)
        return responses

    # ------------------------------------------------------------------
    # Private: inference
    # ------------------------------------------------------------------

    def _run_inference(self, img: np.ndarray) -> dict:
        """
        Run PaddleOCR inference on a BGR ndarray.

        PaddleOCR 3.x predict() accepts an ndarray directly.
        Returns a dict with keys: rec_texts, rec_scores, rec_polys.
        """
        # predict() returns a list with one OCRResult per image
        raw = self._ocr.predict(img)

        if not raw:
            return {"rec_texts": [], "rec_scores": [], "rec_polys": []}

        result = raw[0]  # first (and only) image result

        rec_texts  = result.get("rec_texts",  []) or []
        rec_scores = result.get("rec_scores", []) or []
        rec_polys  = result.get("rec_polys",  []) or []

        # Fallback: use dt_polys if rec_polys is absent
        if not rec_polys:
            rec_polys = result.get("dt_polys", []) or []

        return {
            "rec_texts":  rec_texts,
            "rec_scores": rec_scores,
            "rec_polys":  rec_polys,
        }

    # ------------------------------------------------------------------
    # Private: save outputs
    # ------------------------------------------------------------------

    def _save_outputs(
        self,
        img: np.ndarray,
        results: List[OCRTextResult],
        response: OCRResponse,
        stem: str,
    ) -> None:
        """Save JSON result file and annotated image."""
        import json

        # JSON
        json_path = self.output_dir / (stem + JSON_SUFFIX)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)
        logger.debug("JSON saved: %s", json_path)

        # Annotated image
        ann_path = self.output_dir / (stem + ANNOTATED_IMAGE_SUFFIX)
        annotated = draw_ocr_results(img, results)
        save_annotated_image(annotated, ann_path)
