import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, useAnimations, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { prefersReducedMotion } from '../theme.js';

const AVATAR_URL = '/models/avatar.glb';
const BASE_Y = -1.45; // vertical offset of the placeholder avatar inside the arch

/* Colours per theme so the scene matches the page. */
const PALETTES = {
  light: {
    skin: '#C28E78', hair: '#2A211B', shirt: '#B4421A', eye: '#1F1B16',
    shapes: ['#B4421A', '#E9C9A8', '#3E372F'], ambient: 1.5, key: 2.3, accentLight: '#FFB48A',
  },
  dark: {
    skin: '#C28E78', hair: '#120E0B', shirt: '#F08A5D', eye: '#120E0B',
    shapes: ['#F08A5D', '#6E5A48', '#F3ECE2'], ambient: 1.0, key: 1.7, accentLight: '#FF9A6B',
  },
};

/* Normalised pointer position (-1..1) over the whole window, shared by every object. */
function usePointerRef(enabled) {
  const pointer = useRef({ x: 0, y: 0 });
  useEffect(() => {
    if (!enabled) return undefined;
    const onMove = (e) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = -((e.clientY / window.innerHeight) * 2 - 1);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => window.removeEventListener('pointermove', onMove);
  }, [enabled]);
  return pointer;
}

/* ---------- Placeholder avatar (used until /models/avatar.glb exists) ---------- */
function ProceduralAvatar({ palette, pointer, motion }) {
  const body = useRef();
  const head = useRef();
  const arm = useRef();
  const eyes = useRef();
  const wave = useRef(0);

  useFrame((state, dt) => {
    if (!motion) return;
    const t = state.clock.elapsedTime;
    const { x, y } = pointer.current;
    body.current.rotation.y = THREE.MathUtils.damp(body.current.rotation.y, x * 0.35, 4, dt);
    head.current.rotation.y = THREE.MathUtils.damp(head.current.rotation.y, x * 0.7, 6, dt);
    head.current.rotation.x = THREE.MathUtils.damp(head.current.rotation.x, -y * 0.35, 6, dt);
    body.current.position.y = BASE_Y + Math.sin(t * 1.4) * 0.04;
    // Blink every few seconds.
    eyes.current.scale.y = Math.sin(t * 0.9) > 0.985 ? 0.1 : 1;
    // Wave when clicked.
    if (wave.current > 0) {
      wave.current -= dt;
      arm.current.rotation.z = -2.3 + Math.sin(t * 12) * 0.35;
    } else {
      arm.current.rotation.z = THREE.MathUtils.damp(arm.current.rotation.z, -0.25, 6, dt);
    }
  });

  return (
    <group ref={body} position={[0, BASE_Y, 0]} onClick={() => { wave.current = 1.6; }}
      onPointerOver={() => { document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { document.body.style.cursor = ''; }}>
      {/* torso */}
      <mesh position={[0, 0.4, 0]}>
        <cylinderGeometry args={[0.62, 1.05, 1.9, 7]} />
        <meshStandardMaterial color={palette.shirt} flatShading />
      </mesh>
      {/* neck */}
      <mesh position={[0, 1.3, 0]}>
        <cylinderGeometry args={[0.2, 0.24, 0.3, 8]} />
        <meshStandardMaterial color={palette.skin} flatShading />
      </mesh>
      {/* right arm (waves on click) */}
      <group ref={arm} position={[0.78, 1.0, 0]}>
        <mesh position={[0, -0.45, 0]}>
          <capsuleGeometry args={[0.14, 0.7, 3, 6]} />
          <meshStandardMaterial color={palette.shirt} flatShading />
        </mesh>
      </group>
      <mesh position={[-0.86, 0.5, 0]} rotation={[0, 0, 0.25]}>
        <capsuleGeometry args={[0.14, 0.7, 3, 6]} />
        <meshStandardMaterial color={palette.shirt} flatShading />
      </mesh>
      {/* head */}
      <group ref={head} position={[0, 1.95, 0]}>
        <mesh scale={[0.95, 1.1, 0.95]}>
          <icosahedronGeometry args={[0.62, 1]} />
          <meshStandardMaterial color={palette.skin} flatShading />
        </mesh>
        <mesh position={[0, 0.12, -0.06]} scale={[1, 1, 1]} rotation={[-0.25, 0, 0]}>
          <sphereGeometry args={[0.7, 10, 7, 0, Math.PI * 2, 0, Math.PI * 0.52]} />
          <meshStandardMaterial color={palette.hair} flatShading />
        </mesh>
        <group ref={eyes} position={[0, 0.02, 0.56]}>
          <mesh position={[-0.2, 0, 0]}><boxGeometry args={[0.15, 0.08, 0.05]} /><meshStandardMaterial color={palette.eye} /></mesh>
          <mesh position={[0.2, 0, 0]}><boxGeometry args={[0.15, 0.08, 0.05]} /><meshStandardMaterial color={palette.eye} /></mesh>
        </group>
      </group>
    </group>
  );
}

/* ---------- Real avatar exported from Blender ---------- */
// The GLB has two clips: "Idle" (loops) and "Wave" (plays once when the avatar is clicked).
function GLBAvatar({ pointer, motion }) {
  const group = useRef();
  const { scene, animations } = useGLTF(AVATAR_URL);
  const { actions, mixer } = useAnimations(animations, group);
  const waving = useRef(false);

  useEffect(() => {
    if (!motion) return undefined;
    const idle = actions.Idle || actions[Object.keys(actions)[0]];
    idle?.reset().fadeIn(0.4).play();
    const onDone = (e) => {
      if (e.action === actions.Wave) {
        waving.current = false;
        idle?.reset().fadeIn(0.3).play();
      }
    };
    mixer.addEventListener('finished', onDone);
    return () => {
      mixer.removeEventListener('finished', onDone);
      idle?.fadeOut(0.2);
    };
  }, [actions, mixer, motion]);

  const wave = () => {
    const w = actions.Wave;
    if (!w || w.isRunning()) return;
    waving.current = true;
    actions.Idle?.fadeOut(0.25);
    w.reset().setLoop(THREE.LoopOnce, 1);
    w.clampWhenFinished = false;
    w.fadeIn(0.25).play();
  };

  useFrame((_, dt) => {
    if (!motion) return;
    const { x, y } = pointer.current;
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, x * 0.45, 5, dt);
    group.current.rotation.x = THREE.MathUtils.damp(group.current.rotation.x, -y * 0.08, 5, dt);
    // Slide to the right while waving so the raised arm stays inside the arch.
    group.current.position.x = THREE.MathUtils.damp(group.current.position.x, waving.current ? 0.2 : 0, 4, dt);
  });

  return (
    <group ref={group} position={[0, -1.95, 0]} scale={0.86}
      onClick={wave}
      onPointerOver={() => { document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { document.body.style.cursor = ''; }}>
      <primitive object={scene} />
    </group>
  );
}

/* ---------- Floating objects that react to the mouse ---------- */
function ReactiveShape({ geometry, color, base, depth, spin, pointer, motion }) {
  const mesh = useRef();
  const [hovered, setHovered] = useState(false);
  const burst = useRef(0);

  useFrame((_, dt) => {
    if (!motion) return;
    const m = mesh.current;
    // Parallax: nearer shapes (higher depth) move more with the cursor.
    m.position.x = THREE.MathUtils.damp(m.position.x, base[0] + pointer.current.x * depth, 3, dt);
    m.position.y = THREE.MathUtils.damp(m.position.y, base[1] + pointer.current.y * depth * 0.7, 3, dt);
    // Spin faster when hovered or just clicked.
    burst.current = THREE.MathUtils.damp(burst.current, 0, 2, dt);
    const speed = spin + (hovered ? 1.6 : 0) + burst.current;
    m.rotation.x += dt * speed * 0.6;
    m.rotation.y += dt * speed;
    const target = hovered ? 1.25 : 1;
    m.scale.setScalar(THREE.MathUtils.damp(m.scale.x, target, 8, dt));
  });

  return (
    <Float speed={motion ? 1.6 : 0} rotationIntensity={0} floatIntensity={motion ? 0.8 : 0}>
      <mesh
        ref={mesh}
        position={base}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={() => { setHovered(false); document.body.style.cursor = ''; }}
        onClick={(e) => { e.stopPropagation(); burst.current = 9; }}
      >
        {geometry}
        <meshStandardMaterial color={color} flatShading roughness={0.5} metalness={0.1} />
      </mesh>
    </Float>
  );
}

/* A light that follows the cursor, so the whole scene visibly responds. */
function CursorLight({ pointer, color, motion }) {
  const light = useRef();
  useFrame((_, dt) => {
    if (!motion) return;
    light.current.position.x = THREE.MathUtils.damp(light.current.position.x, pointer.current.x * 4, 4, dt);
    light.current.position.y = THREE.MathUtils.damp(light.current.position.y, pointer.current.y * 3 + 1, 4, dt);
  });
  return <pointLight ref={light} position={[0, 1, 3]} intensity={30} distance={14} color={color} />;
}

function Scene({ theme, hasGlb, motion }) {
  const palette = PALETTES[theme] || PALETTES.light;
  const pointer = usePointerRef(motion);
  const shapes = useMemo(
    () => [
      { key: 'cube', geometry: <boxGeometry args={[0.55, 0.55, 0.55]} />, color: palette.shapes[0], base: [-1.15, 1.25, -1.0], depth: 0.5, spin: 0.5 },
      { key: 'ring', geometry: <torusGeometry args={[0.38, 0.12, 8, 18]} />, color: palette.shapes[1], base: [1.1, 1.5, -0.8], depth: 0.4, spin: 0.7 },
      { key: 'octa', geometry: <octahedronGeometry args={[0.42, 0]} />, color: palette.shapes[2], base: [1.25, 0.15, -1.3], depth: 0.6, spin: 0.4 },
      { key: 'ico', geometry: <icosahedronGeometry args={[0.32, 0]} />, color: palette.shapes[0], base: [-1.25, 0.1, -1.3], depth: 0.35, spin: 0.9 },
    ],
    [palette]
  );

  return (
    <>
      <ambientLight intensity={palette.ambient} />
      <directionalLight position={[3, 5, 4]} intensity={palette.key} />
      <CursorLight pointer={pointer} color={palette.accentLight} motion={motion} />
      <Suspense fallback={null}>
        {hasGlb ? (
          <GLBAvatar pointer={pointer} motion={motion} />
        ) : (
          <ProceduralAvatar palette={palette} pointer={pointer} motion={motion} />
        )}
      </Suspense>
      {shapes.map(({ key, ...s }) => (
        <ReactiveShape key={key} pointer={pointer} motion={motion} {...s} />
      ))}
    </>
  );
}

/* Shown if WebGL is unavailable or the scene crashes. */
function StaticFallback() {
  return (
    <div className="hero3d-fallback" role="img" aria-label="Illustration of the portfolio owner">
      <svg viewBox="0 0 400 520" width="100%" height="100%" aria-hidden="true">
        <path d="M70 520 C70 400 130 350 200 350 C270 350 330 400 330 520 Z" fill="var(--accent)" />
        <rect x="172" y="300" width="56" height="64" rx="18" fill="#9C6B55" />
        <ellipse cx="200" cy="232" rx="70" ry="82" fill="#B98068" />
        <path d="M128 214 C128 150 168 124 204 124 C246 124 274 156 272 214 C262 176 236 160 200 160 C164 160 140 180 128 214 Z" fill="#2A211B" />
        <rect x="168" y="232" width="20" height="8" rx="4" fill="#2A211B" />
        <rect x="212" y="232" width="20" height="8" rx="4" fill="#2A211B" />
      </svg>
    </div>
  );
}

class Boundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(err) { console.warn('3D hero failed, showing static fallback:', err); }
  render() { return this.state.failed ? <StaticFallback /> : this.props.children; }
}

function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

export default function Hero3D({ theme }) {
  const [hasGlb, setHasGlb] = useState(false);
  const [ok] = useState(webglAvailable);
  const motion = !prefersReducedMotion();

  // Use the real Blender avatar when the file has been added to /public/models.
  useEffect(() => {
    let cancelled = false;
    fetch(AVATAR_URL, { method: 'HEAD' })
      .then((r) => {
        const type = r.headers.get('content-type') || '';
        if (!cancelled && r.ok && !type.includes('text/html')) setHasGlb(true);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  if (!ok) return <StaticFallback />;

  return (
    <Boundary>
      <Canvas
        key={hasGlb ? 'glb' : 'proc'}
        frameloop={motion ? 'always' : 'demand'}
        dpr={[1, 2]}
        camera={{ position: [0, 0.4, 6], fov: 38 }}
        gl={{ alpha: true, antialias: true }}
        aria-label="Interactive 3D avatar. Move the mouse to make it look at you; click it to wave."
      >
        <Scene theme={theme} hasGlb={hasGlb} motion={motion} />
      </Canvas>
    </Boundary>
  );
}
