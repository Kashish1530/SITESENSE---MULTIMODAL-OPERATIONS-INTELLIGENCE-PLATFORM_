"""
SiteSense Interactive Visualizer & Operations Agent UI Router
Provides a unified browser dashboard for:
1. Visual Compliance Inspector: Drag-and-drop upload, file picker, 1-click sample images, multi-model YOLO bounding boxes
2. Operations Agent Chat: Live conversational interface calling tools, policy retrieval, SQL queries, and audit trails
"""

import os
import base64
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import cv2
import numpy as np

from vision_service.detector import detector
from inspect_image import draw_bounding_boxes

router = APIRouter(tags=["Visualizer"])

UPLOAD_PREVIEW_DIR = Path("storage/uploads/preview")
UPLOAD_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

SAMPLES_DIR = Path("storage/samples")
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/visualizer", response_class=HTMLResponse)
async def visualizer_page():
    html_content = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SiteSense - Operations Intelligence & Agent Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    body { background-color: #0b0f19; color: #e2e8f0; font-family: ui-sans-serif, system-ui, sans-serif; }
    .dropzone { border: 2px dashed #334155; transition: all 0.2s; }
    .dropzone:hover, .dropzone.dragover { border-color: #3b82f6; background-color: #1e293b; }
    .tab-active { border-bottom: 2px solid #3b82f6; color: #60a5fa; font-weight: 600; }
    .chat-bubble-user { background-color: #1e3a8a; border-radius: 12px 12px 2px 12px; }
    .chat-bubble-agent { background-color: #1e293b; border-radius: 12px 12px 12px 2px; }

    /* Markdown Table & Formatting Styling */
    .chat-content table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin: 0.75rem 0;
      border-radius: 0.5rem;
      overflow: hidden;
      border: 1px solid #334155;
      font-size: 0.75rem;
    }
    .chat-content th {
      background-color: #0f172a;
      color: #93c5fd;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid #334155;
      text-align: left;
    }
    .chat-content td {
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid #1e293b;
      color: #cbd5e1;
      line-height: 1.45;
    }
    .chat-content tr:last-child td {
      border-bottom: none;
    }
    .chat-content tr:nth-child(even) {
      background-color: rgba(15, 23, 42, 0.45);
    }
    .chat-content tr:hover {
      background-color: rgba(51, 65, 85, 0.35);
    }
    .chat-content ul {
      list-style-type: disc;
      margin-left: 1.25rem;
      margin-top: 0.25rem;
      margin-bottom: 0.5rem;
    }
    .chat-content ol {
      list-style-type: decimal;
      margin-left: 1.25rem;
      margin-top: 0.25rem;
      margin-bottom: 0.5rem;
    }
    .chat-content p {
      margin-bottom: 0.5rem;
    }
    .chat-content p:last-child {
      margin-bottom: 0;
    }
    .chat-content strong {
      color: #f8fafc;
      font-weight: 600;
    }
    .chat-content code {
      background-color: #0f172a;
      padding: 0.1rem 0.35rem;
      border-radius: 0.25rem;
      font-family: monospace;
      color: #38bdf8;
      font-size: 0.72rem;
    }
    .chat-content h3 {
      font-size: 0.85rem;
      font-weight: 700;
      color: #93c5fd;
      margin-top: 0.75rem;
      margin-bottom: 0.25rem;
    }
    .chat-content h4 {
      font-size: 0.8rem;
      font-weight: 600;
      color: #e2e8f0;
      margin-top: 0.5rem;
      margin-bottom: 0.25rem;
    }
  </style>
</head>
<body class="min-h-screen p-4 md:p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-4 gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white flex items-center gap-2">
          <span class="bg-blue-600 text-xs uppercase px-2 py-1 rounded font-mono font-semibold">SiteSense</span>
          Multimodal Operations Intelligence Platform
        </h1>
        <p class="text-xs text-slate-400 mt-1">Multi-Model YOLO Ensemble (16-Class & Construction) • Hybrid Policy Retrieval • Autonomous Agent</p>
      </div>
      <div class="flex items-center gap-3">
        <a href="/docs" target="_blank" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition">
          Swagger API Docs ↗
        </a>
        <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Multi-Model Ensemble Active
        </span>
      </div>
    </header>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-800 gap-8 text-sm">
      <button id="tabBtnVisual" class="py-3 px-1 tab-active flex items-center gap-2 transition" onclick="switchTab('visual')">
        📷 1. Visual Compliance Inspector
      </button>
      <button id="tabBtnAgent" class="py-3 px-1 text-slate-400 hover:text-slate-200 flex items-center gap-2 transition" onclick="switchTab('agent')">
        🤖 2. Operations Agent Chat (Module 4)
      </button>
    </div>

    <!-- TAB 1: VISUAL COMPLIANCE INSPECTOR -->
    <div id="tabContentVisual" class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left Column: Upload -->
      <div class="lg:col-span-5 space-y-4">
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h2 class="text-sm font-semibold uppercase text-slate-300 tracking-wider mb-3">Upload Inspection Image</h2>
          
          <!-- Dropzone -->
          <div id="dropzone" class="dropzone rounded-lg p-6 text-center cursor-pointer mb-3">
            <svg class="mx-auto h-10 w-10 text-slate-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
            <p class="text-sm font-medium text-slate-200">Drag & drop image here</p>
            <p class="text-xs text-slate-400 mt-1 mb-3">JPG, PNG, WEBP (Max 15MB)</p>
            <button type="button" id="browseBtn" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition">
              📁 Browse Files on Computer
            </button>
          </div>

          <!-- Hidden File Input (Outside Dropzone to prevent click recursion) -->
          <input type="file" id="fileInput" accept="image/*" class="hidden">

          <!-- 1-Click Sample Previews -->
          <div class="mb-4">
            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Or Choose a 1-Click Sample Inspection Image:</p>
            <div class="grid grid-cols-2 gap-2">
              <button type="button" onclick="loadSampleImage('construction_crane.jpg', 'Construction Crane & Workers')" class="p-2 text-left bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 rounded text-xs text-slate-300 transition">
                🏗️ Crane & Machinery
              </button>
              <button type="button" onclick="loadSampleImage('construction_workers_ppe.jpg', 'Workers PPE Inspection')" class="p-2 text-left bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 rounded text-xs text-slate-300 transition">
                👷 Hardhats & Vests
              </button>
              <button type="button" onclick="loadSampleImage('warehouse_spill.jpg', 'Warehouse Spill Hazard')" class="p-2 text-left bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 rounded text-xs text-slate-300 transition">
                ⚠️ Liquid Spill Hazard
              </button>
              <button type="button" onclick="loadSampleImage('warehouse_obstacle.jpg', 'Walkway Obstacle')" class="p-2 text-left bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 rounded text-xs text-slate-300 transition">
                🚫 Walkway Obstacle
              </button>
            </div>
          </div>

          <!-- Selected File Info & Thumbnail -->
          <div id="filePreviewInfo" class="hidden text-xs text-slate-300 bg-slate-800/80 p-3 rounded-lg border border-slate-700 mb-4 flex items-center justify-between gap-3">
            <img id="thumbnailPreview" class="w-12 h-12 object-cover rounded border border-slate-600" src="" alt="Thumbnail">
            <div class="flex-1 truncate">
              <span id="fileName" class="font-mono font-medium block truncate text-slate-200">image.jpg</span>
              <span id="fileSize" class="text-[11px] text-slate-400">Ready to audit</span>
            </div>
            <button type="button" id="clearBtn" class="text-red-400 hover:text-red-300 font-semibold px-2 py-1">Remove</button>
          </div>

          <!-- Action Button -->
          <button type="button" id="analyzeBtn" class="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-sm transition shadow-lg flex items-center justify-center gap-2">
            <span>🔍 Run Detection & Policy Audit</span>
          </button>
        </div>

        <!-- Detected Classes Breakdown -->
        <div id="detectionsCard" class="hidden bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
          <h3 class="text-xs font-semibold uppercase text-slate-400 tracking-wider">Detected Objects & Classes</h3>
          <div id="detectionsList" class="flex flex-wrap gap-1.5"></div>
        </div>
      </div>

      <!-- Right Column: Visual Result & Compliance Audit -->
      <div class="lg:col-span-7 space-y-4">
        <!-- Image Preview Card -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg min-h-[420px] flex flex-col justify-center items-center relative overflow-hidden">
          <div id="placeholderView" class="text-center text-slate-500 py-16">
            <svg class="mx-auto h-16 w-16 text-slate-700 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
            </svg>
            <p class="text-sm font-medium">Select an image on the left and click "Run Detection & Policy Audit"</p>
            <p class="text-xs text-slate-500 mt-1">Annotated bounding boxes will be rendered here</p>
          </div>

          <div id="loadingView" class="hidden flex flex-col items-center justify-center py-16 space-y-3">
            <div class="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
            <p class="text-xs font-mono text-blue-400">Running multi-model YOLO inference & policy rule check...</p>
          </div>

          <img id="resultImage" class="hidden rounded-lg max-h-[520px] w-auto object-contain border border-slate-700 shadow-2xl">
        </div>

        <!-- Compliance Violations / Status -->
        <div id="complianceCard" class="hidden bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
          <h3 class="text-xs font-semibold uppercase text-slate-400 tracking-wider">Automated Policy Compliance Evaluation</h3>
          <div id="complianceResults" class="space-y-2"></div>
        </div>
      </div>
    </div>

    <!-- TAB 2: AGENT CONVERSATIONAL INTERACTION -->
    <div id="tabContentAgent" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Agent Chat Main Panel -->
      <div class="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col h-[650px]">
        <div class="flex justify-between items-center border-b border-slate-800 pb-3 mb-4">
          <div>
            <h2 class="text-sm font-semibold text-white flex items-center gap-2">
              🤖 SiteSense Autonomous Auditor
            </h2>
            <p class="text-xs text-slate-400">Queries Neon DB, retrieves policy chunks, and runs multi-step reasoning</p>
          </div>
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
            Session: <span id="chatSessionId">active</span>
          </span>
        </div>

        <!-- Message History -->
        <div id="chatMessages" class="flex-1 overflow-y-auto space-y-4 pr-2">
          <!-- Initial Agent Greeting -->
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
              AI
            </div>
            <div class="chat-bubble-agent p-4 text-xs text-slate-200 border border-slate-700 max-w-[85%] space-y-2">
              <p>Hello! I am the <strong>SiteSense Operations Agent</strong>. I can assist you with:</p>
              <ul class="list-disc list-inside space-y-1 text-slate-300">
                <li>Governing policy rules (e.g. <em>"What are the safety rules for forklift operators?"</em>)</li>
                <li>Site inspection findings (e.g. <em>"Did Site 12 pass walkway clearance this week?"</em>)</li>
                <li>Database queries (e.g. <em>"How many sites and inspections do we currently have?"</em>)</li>
                <li>Compliance reports & ticket creation</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Chat Input Bar -->
        <form id="chatForm" class="mt-4 pt-3 border-t border-slate-800 flex gap-2">
          <input 
            type="text" 
            id="chatInput" 
            placeholder="Ask a compliance or site operations question..." 
            class="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            required
          >
          <button 
            type="submit" 
            id="chatSendBtn"
            class="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition shadow disabled:opacity-50"
          >
            <span>Send</span>
          </button>
        </form>
      </div>

      <!-- Quick Prompts & Audit Trace Side Panel -->
      <div class="lg:col-span-4 space-y-4">
        <!-- Quick Prompts Card -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
          <h3 class="text-xs font-semibold uppercase text-slate-400 tracking-wider">Suggested Test Prompts</h3>
          <div class="space-y-1.5 text-xs">
            <button class="w-full text-left p-2 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 transition" onclick="useQuickPrompt('What is the policy for forklift separation, check if Site 12 had any issues with this, and give me the status.')">
              🔍 <strong>Hybrid:</strong> Forklift policy + Site 12 status
            </button>
            <button class="w-full text-left p-2 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 transition" onclick="useQuickPrompt('What does the policy say about pallet stacking height in warehouse zones?')">
              📜 <strong>Policy:</strong> Pallet stacking height rule
            </button>
            <button class="w-full text-left p-2 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 transition" onclick="useQuickPrompt('How many sites and inspections do we currently have in our database?')">
              🗄️ <strong>Database:</strong> Sites & inspections count
            </button>
            <button class="w-full text-left p-2 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 transition" onclick="useQuickPrompt('Generate a compliance report for Site 12.')">
              📋 <strong>Report:</strong> Generate compliance report
            </button>
          </div>
        </div>

        <!-- Real-time Agent Audit Inspector -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
          <h3 class="text-xs font-semibold uppercase text-slate-400 tracking-wider">Latest Run Audit Telemetry</h3>
          <div id="auditTelemetry" class="text-xs space-y-2 text-slate-400">
            <div class="flex justify-between"><span>Route Selected:</span> <span id="auditRoute" class="font-mono text-slate-200">-</span></div>
            <div class="flex justify-between"><span>Tools Called:</span> <span id="auditTools" class="font-mono text-blue-400">-</span></div>
            <div class="flex justify-between"><span>Latency:</span> <span id="auditLatency" class="font-mono text-slate-200">-</span></div>
            <div class="flex justify-between"><span>Token Usage:</span> <span id="auditTokens" class="font-mono text-slate-200">-</span></div>
            <div class="flex justify-between"><span>Audit Run ID:</span> <span id="auditRunId" class="font-mono text-[10px] text-slate-500 truncate max-w-[120px]">-</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Tab Switching
    function switchTab(tab) {
      const tabVisual = document.getElementById('tabContentVisual');
      const tabAgent = document.getElementById('tabContentAgent');
      const btnVisual = document.getElementById('tabBtnVisual');
      const btnAgent = document.getElementById('tabBtnAgent');

      if (tab === 'visual') {
        tabVisual.classList.remove('hidden');
        tabAgent.classList.add('hidden');
        btnVisual.className = 'py-3 px-1 tab-active flex items-center gap-2 transition';
        btnAgent.className = 'py-3 px-1 text-slate-400 hover:text-slate-200 flex items-center gap-2 transition';
      } else {
        tabVisual.classList.add('hidden');
        tabAgent.classList.remove('hidden');
        btnAgent.className = 'py-3 px-1 tab-active flex items-center gap-2 transition';
        btnVisual.className = 'py-3 px-1 text-slate-400 hover:text-slate-200 flex items-center gap-2 transition';
      }
    }

    // Tab 1: Visual Inspector Logic
    const dropzone = document.getElementById('dropzone');
    const browseBtn = document.getElementById('browseBtn');
    const fileInput = document.getElementById('fileInput');
    const filePreviewInfo = document.getElementById('filePreviewInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const thumbnailPreview = document.getElementById('thumbnailPreview');
    const clearBtn = document.getElementById('clearBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');

    const placeholderView = document.getElementById('placeholderView');
    const loadingView = document.getElementById('loadingView');
    const resultImage = document.getElementById('resultImage');
    const detectionsCard = document.getElementById('detectionsCard');
    const detectionsList = document.getElementById('detectionsList');
    const complianceCard = document.getElementById('complianceCard');
    const complianceResults = document.getElementById('complianceResults');

    let selectedFile = null;
    let selectedSampleName = null;

    // File Browser Triggers
    browseBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });

    dropzone.addEventListener('click', (e) => {
      if (e.target !== browseBtn) {
        fileInput.click();
      }
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });

    function handleFileSelection(file) {
      selectedFile = file;
      selectedSampleName = null;
      fileName.textContent = file.name;
      fileSize.textContent = `${(file.size / 1024).toFixed(1)} KB (Selected from Computer)`;
      
      const reader = new FileReader();
      reader.onload = (e) => {
        thumbnailPreview.src = e.target.result;
      };
      reader.readAsDataURL(file);

      filePreviewInfo.classList.remove('hidden');
    }

    async function loadSampleImage(sampleFilename, displayName) {
      selectedSampleName = sampleFilename;
      selectedFile = null;
      fileName.textContent = `${displayName} (${sampleFilename})`;
      fileSize.textContent = "Loaded from SiteSense Sample Repository";
      thumbnailPreview.src = `/visualizer/sample/${sampleFilename}`;
      filePreviewInfo.classList.remove('hidden');
    }

    clearBtn.addEventListener('click', () => {
      selectedFile = null;
      selectedSampleName = null;
      fileInput.value = '';
      filePreviewInfo.classList.add('hidden');
      thumbnailPreview.src = '';
    });

    analyzeBtn.addEventListener('click', async () => {
      if (!selectedFile && !selectedSampleName) {
        alert('Please select or browse an image file first, or choose one of the sample images!');
        return;
      }

      placeholderView.classList.add('hidden');
      resultImage.classList.add('hidden');
      loadingView.classList.remove('hidden');
      detectionsCard.classList.add('hidden');
      complianceCard.classList.add('hidden');

      const formData = new FormData();
      if (selectedFile) {
        formData.append('file', selectedFile);
      } else if (selectedSampleName) {
        formData.append('sample_name', selectedSampleName);
      }

      try {
        const response = await fetch('/visualizer/analyze', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();

        loadingView.classList.add('hidden');

        if (data.annotated_image_base64) {
          resultImage.src = data.annotated_image_base64;
          resultImage.classList.remove('hidden');
        }

        // Render Detections
        detectionsList.innerHTML = '';
        if (data.detections && data.detections.length > 0) {
          data.detections.forEach(d => {
            const pill = document.createElement('span');
            pill.className = 'px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs font-mono text-blue-300';
            pill.textContent = `${d.class_name} (${Math.round(d.confidence * 100)}%)`;
            detectionsList.appendChild(pill);
          });
        } else {
          detectionsList.innerHTML = '<span class="text-xs text-slate-500">No objects detected above threshold</span>';
        }
        detectionsCard.classList.remove('hidden');

        // Render Compliance Checks
        complianceResults.innerHTML = '';
        if (data.violations && data.violations.length > 0) {
          data.violations.forEach(v => {
            const item = document.createElement('div');
            item.className = 'p-3 rounded-lg border border-red-900/60 bg-red-950/30 text-xs space-y-1';
            item.innerHTML = `
              <div class="flex items-center justify-between">
                <span class="font-semibold text-red-400">[VIOLATION] ${v.rule}</span>
                <span class="uppercase font-mono text-[10px] px-1.5 py-0.5 rounded bg-red-900/80 text-red-200">${v.severity}</span>
              </div>
              <p class="text-slate-300">${v.desc}</p>
              <div class="text-[11px] text-red-300/80 font-mono">Action: Proposed Corrective Maintenance Ticket</div>
            `;
            complianceResults.appendChild(item);
          });
        } else {
          const pass = document.createElement('div');
          pass.className = 'p-3 rounded-lg border border-emerald-900/60 bg-emerald-950/30 text-xs flex items-center gap-2 text-emerald-400';
          pass.innerHTML = `<span>✓</span> <span><strong>Compliant:</strong> All policy rules passed. No safety hazards flagged.</span>`;
          complianceResults.appendChild(pass);
        }
        complianceCard.classList.remove('hidden');

      } catch (err) {
        loadingView.classList.add('hidden');
        placeholderView.classList.remove('hidden');
        alert('Analysis error: ' + err.message);
      }
    });

    // Tab 2: Agent Chat Logic
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatMessages = document.getElementById('chatMessages');

    const auditRoute = document.getElementById('auditRoute');
    const auditTools = document.getElementById('auditTools');
    const auditLatency = document.getElementById('auditLatency');
    const auditTokens = document.getElementById('auditTokens');
    const auditRunId = document.getElementById('auditRunId');

    function useQuickPrompt(text) {
      chatInput.value = text;
      switchTab('agent');
      chatInput.focus();
    }

    function formatMarkdown(text) {
      if (!text) return '';
      if (typeof marked !== 'undefined' && marked.parse) {
        try {
          return marked.parse(text);
        } catch (e) {
          console.warn('Marked parse error:', e);
        }
      }

      // Robust Pure-JS fallback parser for Markdown tables and formatting
      let lines = text.split('\n');
      let html = [];
      let inTable = false;
      let tableRows = [];

      function flushTable() {
        if (tableRows.length === 0) return;
        let tHtml = '<div class="overflow-x-auto my-2"><table>';
        let isHeader = true;
        for (let r of tableRows) {
          let cols = r.split('|').map(c => c.trim()).filter((c, idx, arr) => (idx > 0 && idx < arr.length - 1) || (idx === 0 && c !== '') || (idx === arr.length - 1 && c !== ''));
          if (cols.length === 0) continue;
          if (cols.every(c => /^[:\s\-]+$/.test(c))) {
            isHeader = false;
            continue;
          }
          if (isHeader) {
            tHtml += '<thead><tr>' + cols.map(c => `<th>${formatInline(c)}</th>`).join('') + '</tr></thead><tbody>';
            isHeader = false;
          } else {
            tHtml += '<tr>' + cols.map(c => `<td>${formatInline(c)}</td>`).join('') + '</tr>';
          }
        }
        tHtml += '</tbody></table></div>';
        html.push(tHtml);
        tableRows = [];
        inTable = false;
      }

      function formatInline(str) {
        return str
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/`([^`]+)`/g, '<code>$1</code>');
      }

      for (let line of lines) {
        let trimmed = line.trim();
        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
          inTable = true;
          tableRows.push(trimmed);
        } else {
          if (inTable) flushTable();
          if (trimmed.startsWith('### ')) {
            html.push(`<h4>${formatInline(trimmed.slice(4))}</h4>`);
          } else if (trimmed.startsWith('## ')) {
            html.push(`<h3>${formatInline(trimmed.slice(3))}</h3>`);
          } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            html.push(`<li>${formatInline(trimmed.slice(2))}</li>`);
          } else if (trimmed) {
            html.push(`<p>${formatInline(trimmed)}</p>`);
          }
        }
      }
      if (inTable) flushTable();
      return html.join('');
    }

    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const question = chatInput.value.trim();
      if (!question) return;

      // Add User Message
      const userDiv = document.createElement('div');
      userDiv.className = 'flex items-start justify-end gap-3';
      userDiv.innerHTML = `
        <div class="chat-bubble-user p-4 text-xs text-white max-w-[85%] shadow">
          ${question.replace(/</g, "&lt;")}
        </div>
      `;
      chatMessages.appendChild(userDiv);
      chatInput.value = '';
      chatSendBtn.disabled = true;

      // Add Loading indicator
      const loadDiv = document.createElement('div');
      loadDiv.id = 'agentThinking';
      loadDiv.className = 'flex items-start gap-3';
      loadDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
          AI
        </div>
        <div class="chat-bubble-agent p-4 text-xs text-slate-400 border border-slate-700 flex items-center gap-2">
          <div class="w-2 h-2 rounded-full bg-blue-400 animate-ping"></div>
          <span>Reasoning, retrieving policies & auditing database...</span>
        </div>
      `;
      chatMessages.appendChild(loadDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;

      try {
        const response = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: question, session_id: 'web_session_01' })
        });
        const data = await response.json();
        const thinkingElem = document.getElementById('agentThinking');
        if (thinkingElem) thinkingElem.remove();

        // Render Agent Response
        const agentDiv = document.createElement('div');
        agentDiv.className = 'flex items-start gap-3';

        // Format Markdown with table support
        let formattedAnswer = formatMarkdown(data.answer || '');

        agentDiv.innerHTML = `
          <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
            AI
          </div>
          <div class="chat-bubble-agent p-4 text-xs text-slate-200 border border-slate-700 max-w-[90%] space-y-2 shadow">
            <div class="chat-content leading-relaxed">${formattedAnswer}</div>
            ${data.tools_called && data.tools_called.length > 0 ? `
              <div class="pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400">
                Tools invoked: ${data.tools_called.map(t => `<span class="text-blue-400">${t.tool || t}</span>`).join(' → ')}
              </div>
            ` : ''}
          </div>
        `;
        chatMessages.appendChild(agentDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Update Audit Telemetry Panel
        auditRoute.textContent = data.route || 'general';
        auditTools.textContent = (data.tools_called && data.tools_called.length > 0) 
          ? data.tools_called.map(t => t.tool || t).join(', ') 
          : 'None';
        auditLatency.textContent = data.latency ? `${data.latency}s` : '-';
        auditTokens.textContent = data.tokens ? `${data.tokens}` : '-';
        auditRunId.textContent = data.audit_run_id || '-';

      } catch (err) {
        const thinkingElem = document.getElementById('agentThinking');
        if (thinkingElem) thinkingElem.remove();
        alert('Chat error: ' + err.message);
      } finally {
        chatSendBtn.disabled = false;
        chatInput.focus();
      }
    });
  </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/visualizer/sample/{sample_name}")
async def get_sample_image(sample_name: str):
    """Serves sample image files directly for instant UI preview."""
    sample_path = SAMPLES_DIR / sample_name
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample image not found")
    with open(sample_path, "rb") as f:
        img_bytes = f.read()
    media_type = "image/jpeg" if sample_name.lower().endswith(".jpg") else "image/png"
    from fastapi.responses import Response
    return Response(content=img_bytes, media_type=media_type)


@router.post("/visualizer/analyze")
async def analyze_visual_upload(
    file: Optional[UploadFile] = File(None),
    sample_name: Optional[str] = Form(None)
):
    """
    Accepts either an uploaded file OR a sample image name, runs detector ensemble,
    draws bounding boxes, checks policy compliance, and returns base64 image + findings.
    """
    if file:
        filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        save_path = UPLOAD_PREVIEW_DIR / filename
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
    elif sample_name:
        src_sample = SAMPLES_DIR / sample_name
        if not src_sample.exists():
            raise HTTPException(status_code=404, detail="Sample file not found")
        filename = f"sample_{sample_name}"
        save_path = UPLOAD_PREVIEW_DIR / filename
        shutil.copy(str(src_sample), str(save_path))
    else:
        raise HTTPException(status_code=400, detail="Either file or sample_name must be provided")

    # 1. Run detection
    detections = detector.detect(str(save_path))

    # 2. Draw bounding boxes
    annotated_path = UPLOAD_PREVIEW_DIR / f"annotated_{filename}"
    draw_bounding_boxes(str(save_path), detections, str(annotated_path))

    # 3. Read annotated image to Base64
    with open(annotated_path, "rb") as f_out:
        b64_img = base64.b64encode(f_out.read()).decode("utf-8")
        img_mime = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
        data_uri = f"data:{img_mime};base64,{b64_img}"

    # 4. Check compliance rules against detected classes
    detected_classes = {d["class_name"].lower() for d in detections}
    violations = []
    
    # PPE Hard Hat Check (SITE-PPE-01)
    if "no_hardhat" in detected_classes or ("person" in detected_classes and "hardhat" not in detected_classes and "safety_helmet" not in detected_classes):
        violations.append({
            "rule": "Mandatory PPE - Hard Hat (SITE-PPE-01)",
            "severity": "critical",
            "desc": "Active personnel observed on site without approved hard hat."
        })

    # PPE Hi-Vis Vest Check (SITE-PPE-02)
    if "no_safety_vest" in detected_classes or ("person" in detected_classes and "safety_vest" not in detected_classes):
        violations.append({
            "rule": "Mandatory PPE - Hi-Vis Vest (SITE-PPE-02)",
            "severity": "major",
            "desc": "Active personnel observed on site without high-visibility reflective safety vest."
        })

    # Heavy Machinery / Construction Equipment Perimeter (SITE-ZONE-01)
    heavy_equipment = detected_classes.intersection({"crane", "excavator", "machinery", "truck"})
    if heavy_equipment and "person" in detected_classes and "safety_cone" not in detected_classes:
        equip_names = ", ".join([e.title() for e in heavy_equipment])
        violations.append({
            "rule": "Heavy Equipment Perimeter Safety (SITE-ZONE-01)",
            "severity": "critical",
            "desc": f"Heavy equipment ({equip_names}) operating near pedestrian personnel without barricades or safety cones."
        })

    # Forklift Pedestrian Separation (WH-FORK-01)
    if "forklift" in detected_classes and "person" in detected_classes:
        violations.append({
            "rule": "Forklift Pedestrian Separation (WH-FORK-01)",
            "severity": "critical",
            "desc": "Forklift operating within 2.5m buffer of unsegregated pedestrian walkway."
        })

    # Liquid Spill Containment (WH-ENV-01)
    if "spill" in detected_classes and "safety_cone" not in detected_classes:
        violations.append({
            "rule": "Liquid Spill Containment (WH-ENV-01)",
            "severity": "critical",
            "desc": "Liquid spill detected without mandatory warning safety cones."
        })

    # Emergency Walkway Obstacle (WH-CLR-01)
    if "obstacle" in detected_classes:
        violations.append({
            "rule": "Emergency Walkway Egress (WH-CLR-01)",
            "severity": "major",
            "desc": "Obstacle obstructing marked aisle or egress path."
        })

    return {
        "status": "success",
        "filename": filename,
        "annotated_image_base64": data_uri,
        "detections_count": len(detections),
        "detections": detections,
        "violations": violations
    }
