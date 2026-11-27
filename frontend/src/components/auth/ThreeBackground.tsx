import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface RoamingObject {
  mesh: THREE.Mesh | THREE.LineSegments
  vx: number
  vy: number
  vz: number
  rx: number
  ry: number
  rz: number
  boundsX: number
  boundsY: number
  boundsZ: number
}

export default function ThreeBackground() {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Avoid running in automated test or non-browser environments
    if ((import.meta as any).env?.MODE === 'test' || typeof window === 'undefined' || !mountRef.current) return

    // Verify WebGL availability safely
    try {
      const testCanvas = document.createElement('canvas')
      const gl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl')
      if (!gl) return
    } catch {
      return
    }

    const container = mountRef.current
    let width = container.clientWidth || window.innerWidth
    let height = container.clientHeight || window.innerHeight

    // 1. Scene & Camera Setup
    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0x070b19, 0.018)

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000)
    camera.position.set(0, 0, 32)

    // 2. WebGL Renderer
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      })
      renderer.setSize(width, height)
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.setClearColor(0x000000, 0)
      container.appendChild(renderer.domElement)
    } catch (e) {
      console.warn('WebGL initialization failed, falling back:', e)
      return
    }

    // 3. Dynamic Lighting Setup
    const ambientLight = new THREE.AmbientLight(0x38bdf8, 0.7)
    scene.add(ambientLight)

    const pointLightBlue = new THREE.PointLight(0x3b82f6, 4, 60)
    pointLightBlue.position.set(12, 10, 15)
    scene.add(pointLightBlue)

    const pointLightCyan = new THREE.PointLight(0x06b6d4, 3.5, 60)
    pointLightCyan.position.set(-15, -8, 12)
    scene.add(pointLightCyan)

    const pointLightPurple = new THREE.PointLight(0x8b5cf6, 3, 50)
    pointLightPurple.position.set(0, 14, 10)
    scene.add(pointLightPurple)

    // Mouse tracking point light
    const mouseLight = new THREE.PointLight(0x60a5fa, 2.5, 30)
    mouseLight.position.set(0, 0, 15)
    scene.add(mouseLight)

    // 4. Materials Palette
    const cyanWireMaterial = new THREE.MeshStandardMaterial({
      color: 0x06b6d4,
      emissive: 0x0284c7,
      emissiveIntensity: 0.35,
      wireframe: true,
      roughness: 0.2,
      metalness: 0.8,
    })

    const blueSolidMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x1d4ed8,
      emissive: 0x1e40af,
      emissiveIntensity: 0.2,
      roughness: 0.15,
      metalness: 0.85,
      transmission: 0.3,
      opacity: 0.85,
      transparent: true,
      reflectivity: 0.9,
    })

    const purpleGlossMaterial = new THREE.MeshStandardMaterial({
      color: 0x7c3aed,
      emissive: 0x4c1d95,
      emissiveIntensity: 0.3,
      roughness: 0.2,
      metalness: 0.7,
      wireframe: false,
    })

    const goldSensorMaterial = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0369a1,
      emissiveIntensity: 0.4,
      roughness: 0.3,
      metalness: 0.9,
    })

    // 5. Create Roaming 3D Objects
    const roamingObjects: RoamingObject[] = []

    const objectBlueprints = [
      // Large Icosahedrons
      {
        geom: new THREE.IcosahedronGeometry(2.8, 1),
        mat: cyanWireMaterial,
        pos: [-18, 9, -5],
        speed: [0.008, 0.012, 0.005],
        rot: [0.006, 0.008, 0.004],
      },
      {
        geom: new THREE.IcosahedronGeometry(3.2, 0),
        mat: blueSolidMaterial,
        pos: [19, -8, -6],
        speed: [-0.009, 0.007, -0.004],
        rot: [0.005, 0.007, 0.003],
      },
      // Torus Knots & Rings
      {
        geom: new THREE.TorusKnotGeometry(2.0, 0.55, 64, 16),
        mat: purpleGlossMaterial,
        pos: [-16, -11, -8],
        speed: [0.007, -0.008, 0.006],
        rot: [0.01, 0.012, 0.007],
      },
      {
        geom: new THREE.TorusGeometry(3.0, 0.35, 24, 48),
        mat: cyanWireMaterial,
        pos: [17, 10, -4],
        speed: [-0.006, -0.009, 0.004],
        rot: [0.008, 0.01, 0.005],
      },
      // Dodecahedrons & Octahedrons
      {
        geom: new THREE.DodecahedronGeometry(2.2, 0),
        mat: goldSensorMaterial,
        pos: [-22, 0, -10],
        speed: [0.009, 0.006, -0.005],
        rot: [0.007, 0.009, 0.006],
      },
      {
        geom: new THREE.OctahedronGeometry(2.4, 0),
        mat: blueSolidMaterial,
        pos: [21, 2, -7],
        speed: [-0.007, 0.008, -0.006],
        rot: [0.009, 0.005, 0.008],
      },
      // Floating Multimodal Sensor Cubes with glowing outlines
      {
        geom: new THREE.BoxGeometry(2.2, 2.2, 2.2),
        mat: cyanWireMaterial,
        pos: [-11, 14, -12],
        speed: [0.011, -0.007, 0.008],
        rot: [0.012, 0.008, 0.01],
      },
      {
        geom: new THREE.BoxGeometry(2.0, 2.0, 2.0),
        mat: purpleGlossMaterial,
        pos: [12, -14, -10],
        speed: [-0.008, 0.01, -0.007],
        rot: [0.007, 0.011, 0.009],
      },
      // Orbiting Micro Polyhedra (Foreground Depth)
      {
        geom: new THREE.TetrahedronGeometry(1.4, 0),
        mat: goldSensorMaterial,
        pos: [-8, -12, 2],
        speed: [0.012, 0.011, -0.008],
        rot: [0.015, 0.012, 0.008],
      },
      {
        geom: new THREE.IcosahedronGeometry(1.5, 0),
        mat: cyanWireMaterial,
        pos: [8, 12, 3],
        speed: [-0.011, -0.009, 0.007],
        rot: [0.013, 0.016, 0.01],
      },
      {
        geom: new THREE.OctahedronGeometry(1.6, 0),
        mat: blueSolidMaterial,
        pos: [-24, 12, -15],
        speed: [0.008, -0.006, 0.005],
        rot: [0.008, 0.01, 0.006],
      },
      {
        geom: new THREE.TorusGeometry(1.8, 0.25, 16, 32),
        mat: purpleGlossMaterial,
        pos: [24, -12, -14],
        speed: [-0.007, 0.009, -0.005],
        rot: [0.012, 0.007, 0.014],
      },
    ]

    objectBlueprints.forEach((bp) => {
      const mesh = new THREE.Mesh(bp.geom, bp.mat)
      mesh.position.set(bp.pos[0], bp.pos[1], bp.pos[2])
      scene.add(mesh)

      // Add a subtle wireframe companion to solid meshes for a high-tech CAD look
      if (bp.mat !== cyanWireMaterial) {
        const wireframeGeom = new THREE.WireframeGeometry(bp.geom)
        const wireframeLine = new THREE.LineSegments(
          wireframeGeom,
          new THREE.LineBasicMaterial({
            color: 0x93c5fd,
            transparent: true,
            opacity: 0.35,
          })
        )
        mesh.add(wireframeLine)
      }

      roamingObjects.push({
        mesh,
        vx: bp.speed[0],
        vy: bp.speed[1],
        vz: bp.speed[2],
        rx: bp.rot[0],
        ry: bp.rot[1],
        rz: bp.rot[2],
        boundsX: 28,
        boundsY: 17,
        boundsZ: 14,
      })
    })

    // 6. Ambient Constellation Particles
    const particlesCount = 70
    const particlePositions = new Float32Array(particlesCount * 3)
    const particleVelocities: { x: number; y: number; z: number }[] = []

    for (let i = 0; i < particlesCount; i++) {
      particlePositions[i * 3] = (Math.random() - 0.5) * 55
      particlePositions[i * 3 + 1] = (Math.random() - 0.5) * 35
      particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 25
      particleVelocities.push({
        x: (Math.random() - 0.5) * 0.015,
        y: (Math.random() - 0.5) * 0.015,
        z: (Math.random() - 0.5) * 0.01,
      })
    }

    const particlesGeometry = new THREE.BufferGeometry()
    particlesGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(particlePositions, 3)
    )

    const particlesMaterial = new THREE.PointsMaterial({
      color: 0x67e8f9,
      size: 0.35,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    })

    const particleSystem = new THREE.Points(particlesGeometry, particlesMaterial)
    scene.add(particleSystem)

    // 7. Interactive Mouse Parallax
    let targetMouseX = 0
    let targetMouseY = 0
    let currentMouseX = 0
    let currentMouseY = 0

    const handleMouseMove = (event: MouseEvent) => {
      targetMouseX = (event.clientX / window.innerWidth) * 2 - 1
      targetMouseY = -(event.clientY / window.innerHeight) * 2 + 1
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })

    // 8. Handle Window Resize
    const handleResize = () => {
      if (!container) return
      width = container.clientWidth || window.innerWidth
      height = container.clientHeight || window.innerHeight
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    }

    window.addEventListener('resize', handleResize)

    // 9. Animation & Roaming Physics Loop
    let animationFrameId: number
    let clock = new THREE.Clock()

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      const elapsedTime = clock.getElapsedTime()

      // Smooth mouse lerp
      currentMouseX += (targetMouseX - currentMouseX) * 0.04
      currentMouseY += (targetMouseY - currentMouseY) * 0.04

      // Gentle Camera Parallax
      camera.position.x = currentMouseX * 3.5
      camera.position.y = currentMouseY * 2.5
      camera.lookAt(0, 0, 0)

      // Move mouse point light
      mouseLight.position.x = currentMouseX * 18
      mouseLight.position.y = currentMouseY * 12

      // Orbit ambient point lights on smooth Lissajous figures
      pointLightBlue.position.x = Math.sin(elapsedTime * 0.7) * 16
      pointLightBlue.position.y = Math.cos(elapsedTime * 0.5) * 12
      pointLightCyan.position.x = Math.cos(elapsedTime * 0.6) * -16
      pointLightCyan.position.y = Math.sin(elapsedTime * 0.8) * -12

      // Animate Roaming 3D Objects
      roamingObjects.forEach((obj) => {
        // Continuous rotation
        obj.mesh.rotation.x += obj.rx
        obj.mesh.rotation.y += obj.ry
        obj.mesh.rotation.z += obj.rz

        // Position updates
        obj.mesh.position.x += obj.vx
        obj.mesh.position.y += obj.vy
        obj.mesh.position.z += obj.vz

        // Bounce smoothly off boundaries
        if (Math.abs(obj.mesh.position.x) > obj.boundsX) {
          obj.vx *= -1
          obj.mesh.position.x = Math.sign(obj.mesh.position.x) * obj.boundsX
        }
        if (Math.abs(obj.mesh.position.y) > obj.boundsY) {
          obj.vy *= -1
          obj.mesh.position.y = Math.sign(obj.mesh.position.y) * obj.boundsY
        }
        if (Math.abs(obj.mesh.position.z) > obj.boundsZ) {
          obj.vz *= -1
          obj.mesh.position.z = Math.sign(obj.mesh.position.z) * obj.boundsZ
        }
      })

      // Drift Constellation Particles
      const positions = particlesGeometry.attributes.position.array as Float32Array
      for (let i = 0; i < particlesCount; i++) {
        const vel = particleVelocities[i]
        positions[i * 3] += vel.x
        positions[i * 3 + 1] += vel.y
        positions[i * 3 + 2] += vel.z

        // Wrap around bounds
        if (Math.abs(positions[i * 3]) > 30) positions[i * 3] *= -0.98
        if (Math.abs(positions[i * 3 + 1]) > 20) positions[i * 3 + 1] *= -0.98
        if (Math.abs(positions[i * 3 + 2]) > 15) positions[i * 3 + 2] *= -0.98
      }
      particlesGeometry.attributes.position.needsUpdate = true

      renderer.render(scene, camera)
    }

    animate()

    // 10. Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('resize', handleResize)

      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }

      // Dispose Three.js resources
      roamingObjects.forEach((obj) => {
        if ('geometry' in obj.mesh) obj.mesh.geometry.dispose()
      })
      particlesGeometry.dispose()
      particlesMaterial.dispose()
      renderer.dispose()
    }
  }, [])

  return (
    <div
      ref={mountRef}
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
      style={{
        background:
          'radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.7) 0%, rgba(2, 6, 23, 0.98) 100%)',
      }}
    />
  )
}
