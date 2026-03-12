import { useRef, useEffect, useMemo } from 'react';
import * as THREE from 'three';
import {
  vertexShader,
  fragmentShader,
  particleVertexShader,
  particleFragmentShader,
} from '../shaders/background';

interface WebGLBackgroundProps {
  scrollProgress: number;
  mouseX: number;
  mouseY: number;
  theme: 'light' | 'dark';
}

export default function WebGLBackground({ scrollProgress, mouseX, mouseY, theme }: WebGLBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const meshUniformsRef = useRef<Record<string, THREE.IUniform> | null>(null);
  const particleUniformsRef = useRef<Record<string, THREE.IUniform> | null>(null);
  const frameRef = useRef<number>(0);
  const clockRef = useRef(new THREE.Clock());

  const targetMouse = useRef({ x: 0.5, y: 0.5 });
  const smoothMouse = useRef({ x: 0.5, y: 0.5 });
  const targetScroll = useRef(0);
  const smoothScroll = useRef(0);
  const targetTheme = useRef(0);
  const smoothTheme = useRef(0);

  const particleCount = useMemo(() => {
    if (typeof window === 'undefined') return 200;
    return window.innerWidth < 768 ? 100 : 300;
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 3;
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: false,
      powerPreference: 'high-performance',
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const meshUniforms = {
      uTime: { value: 0 },
      uScrollProgress: { value: 0 },
      uMouse: { value: new THREE.Vector2(0.5, 0.5) },
      uTheme: { value: 0 },
    };
    meshUniformsRef.current = meshUniforms;

    const planeGeo = new THREE.PlaneGeometry(8, 6, 64, 48);
    const planeMat = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: meshUniforms,
      transparent: true,
      depthWrite: false,
    });
    const plane = new THREE.Mesh(planeGeo, planeMat);
    plane.position.z = -1;
    scene.add(plane);

    const pUniforms = {
      uTime: { value: 0 },
      uScrollProgress: { value: 0 },
      uTheme: { value: 0 },
    };
    particleUniformsRef.current = pUniforms;

    const positions = new Float32Array(particleCount * 3);
    const scales = new Float32Array(particleCount);
    const speeds = new Float32Array(particleCount);
    const offsets = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 8;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 6;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 3;
      scales[i] = Math.random() * 0.8 + 0.2;
      speeds[i] = Math.random() * 0.8 + 0.2;
      offsets[i] = Math.random() * Math.PI * 2;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('aScale', new THREE.BufferAttribute(scales, 1));
    particleGeo.setAttribute('aSpeed', new THREE.BufferAttribute(speeds, 1));
    particleGeo.setAttribute('aOffset', new THREE.BufferAttribute(offsets, 1));

    const particleMat = new THREE.ShaderMaterial({
      vertexShader: particleVertexShader,
      fragmentShader: particleFragmentShader,
      uniforms: pUniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    const onResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', onResize);

    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      const elapsed = clockRef.current.getElapsedTime();

      smoothMouse.current.x += (targetMouse.current.x - smoothMouse.current.x) * 0.05;
      smoothMouse.current.y += (targetMouse.current.y - smoothMouse.current.y) * 0.05;
      smoothScroll.current += (targetScroll.current - smoothScroll.current) * 0.08;
      smoothTheme.current += (targetTheme.current - smoothTheme.current) * 0.04;

      if (meshUniformsRef.current) {
        meshUniformsRef.current.uTime.value = elapsed;
        meshUniformsRef.current.uScrollProgress.value = smoothScroll.current;
        meshUniformsRef.current.uTheme.value = smoothTheme.current;
        (meshUniformsRef.current.uMouse.value as THREE.Vector2).set(
          smoothMouse.current.x,
          1.0 - smoothMouse.current.y
        );
      }

      if (particleUniformsRef.current) {
        particleUniformsRef.current.uTime.value = elapsed;
        particleUniformsRef.current.uScrollProgress.value = smoothScroll.current;
        particleUniformsRef.current.uTheme.value = smoothTheme.current;
      }

      camera.position.x = (smoothMouse.current.x - 0.5) * 0.3;
      camera.position.y = (smoothMouse.current.y - 0.5) * -0.2;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      planeGeo.dispose();
      planeMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [particleCount]);

  useEffect(() => {
    targetMouse.current = { x: mouseX, y: mouseY };
  }, [mouseX, mouseY]);

  useEffect(() => {
    targetScroll.current = scrollProgress;
  }, [scrollProgress]);

  useEffect(() => {
    targetTheme.current = theme === 'light' ? 1.0 : 0.0;
  }, [theme]);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-0 pointer-events-none"
      style={{ opacity: 0.6 }}
    />
  );
}
