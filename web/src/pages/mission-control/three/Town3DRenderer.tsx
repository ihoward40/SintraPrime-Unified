import { Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { PointerLockControls } from '@react-three/drei';
import * as THREE from 'three';
import {
  GRAPHICS_PRESETS,
  type GraphicsPreset,
  type SpatialActivity,
  type TownWorldState,
} from './townWorld';
import './Town3DRenderer.css';

type RendererProps = {
  world: TownWorldState;
  preset: GraphicsPreset;
  onExit: () => void;
};

const DISTRICT_COLORS: Record<string, string> = {
  citadel: '#d6ad55',
  'town-hall': '#35f2d0',
  constitution: '#e5bd63',
  agents: '#45c9ff',
  evidence: '#79f0c8',
  build: '#8da7ff',
  finance: '#d8b66a',
  creative: '#d684ff',
};

function DistrictBuilding({ district }: { district: TownWorldState['districts'][number] }) {
  const color = DISTRICT_COLORS[district.id] ?? '#35f2d0';
  const emissive = new THREE.Color(color).multiplyScalar(.18);
  return (
    <group position={[district.position.x, district.scale.y / 2, district.position.z]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[district.scale.x, district.scale.y, district.scale.z]} />
        <meshStandardMaterial
          color="#081418"
          metalness={.78}
          roughness={.28}
          emissive={emissive}
          emissiveIntensity={district.activity}
        />
      </mesh>
      <mesh position={[0, district.scale.y / 2 + .35, 0]}>
        <boxGeometry args={[district.scale.x * .82, .28, district.scale.z * .82]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.4} />
      </mesh>
    </group>
  );
}

function Roads() {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, .012, 8]} receiveShadow>
        <planeGeometry args={[8, 90]} />
        <meshStandardMaterial color="#091114" metalness={.5} roughness={.7} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, Math.PI / 2]} position={[0, .014, 5]} receiveShadow>
        <planeGeometry args={[8, 70]} />
        <meshStandardMaterial color="#091114" metalness={.5} roughness={.7} />
      </mesh>
      {[-1.4, 1.4].map((x) => (
        <mesh key={x} rotation={[-Math.PI / 2, 0, 0]} position={[x, .02, 8]}>
          <planeGeometry args={[.07, 88]} />
          <meshBasicMaterial color="#d6ad55" />
        </mesh>
      ))}
    </group>
  );
}

function AgentAvatar({ agent, index }: { agent: TownWorldState['agents'][number]; index: number }) {
  const pulse = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!pulse.current) return;
    const active = agent.state === 'working' || agent.state === 'awaiting-approval';
    pulse.current.scale.setScalar(active ? 1 + Math.sin(clock.elapsedTime * 2 + index) * .08 : 1);
  });
  const color = agent.state === 'blocked' ? '#d6ad55'
    : agent.state === 'awaiting-approval' ? '#ffcf6b'
    : agent.state === 'working' ? '#35f2d0'
    : '#678b88';
  const base = agent.district === 'constitution' ? [-24, 0, -8] : [24, 0, -8];
  return (
    <group position={[base[0] + agent.position.x, .8, base[2] + agent.position.z]}>
      <mesh ref={pulse} castShadow>
        <capsuleGeometry args={[.28, .72, 5, 10]} />
        <meshStandardMaterial color="#0b171b" metalness={.6} roughness={.3} emissive={color} emissiveIntensity={.45} />
      </mesh>
      <mesh position={[0, .88, 0]}>
        <sphereGeometry args={[.24, 14, 14]} />
        <meshStandardMaterial color={color} metalness={.55} roughness={.25} />
      </mesh>
    </group>
  );
}

function DataFlow({ flow, index }: { flow: SpatialActivity; index: number }) {
  const source = useMemo(() => {
    const from = TOWN_POINT[flow.from];
    const to = TOWN_POINT[flow.to];
    return { from, to };
  }, [flow.from, flow.to]);
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = (clock.elapsedTime * (.14 + flow.intensity * .2) + index * .31) % 1;
    ref.current.position.lerpVectors(source.from, source.to, t);
    ref.current.position.y = 1.2 + Math.sin(t * Math.PI) * 4;
  });
  const color = flow.kind === 'approval' ? '#d6ad55' : '#35f2d0';
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[.14 + flow.intensity * .1, 10, 10]} />
      <meshBasicMaterial color={color} />
    </mesh>
  );
}

const TOWN_POINT: Record<string, THREE.Vector3> = {
  citadel: new THREE.Vector3(0, 1, -18),
  'town-hall': new THREE.Vector3(0, 1, 0),
  constitution: new THREE.Vector3(-24, 1, -8),
  agents: new THREE.Vector3(24, 1, -8),
  evidence: new THREE.Vector3(-24, 1, 18),
  build: new THREE.Vector3(24, 1, 18),
  finance: new THREE.Vector3(-10, 1, 34),
  creative: new THREE.Vector3(10, 1, 34),
};

function TownHallInterior() {
  const seats = Array.from({ length: 12 }, (_, i) => {
    const angle = (i / 12) * Math.PI * 2;
    return [Math.cos(angle) * 4.2, Math.sin(angle) * 4.2] as const;
  });
  return (
    <group position={[0, .1, 0]}>
      <mesh position={[0, .22, 0]}>
        <cylinderGeometry args={[2.3, 2.3, .45, 32]} />
        <meshStandardMaterial color="#101d20" metalness={.7} roughness={.3} />
      </mesh>
      {seats.map(([x, z], i) => (
        <mesh key={i} position={[x, .42, z]} rotation={[0, -Math.atan2(z, x) + Math.PI / 2, 0]}>
          <boxGeometry args={[.8, .8, .8]} />
          <meshStandardMaterial color="#15272a" metalness={.45} roughness={.5} />
        </mesh>
      ))}
      <pointLight position={[0, 5, 0]} intensity={16} distance={18} color="#35f2d0" />
    </group>
  );
}

function FirstPersonMovement() {
  const keys = useRef(new Set<string>());
  const direction = useMemo(() => new THREE.Vector3(), []);
  const forward = useMemo(() => new THREE.Vector3(), []);
  const right = useMemo(() => new THREE.Vector3(), []);

  useEffect(() => {
    const down = (event: KeyboardEvent) => keys.current.add(event.code);
    const up = (event: KeyboardEvent) => keys.current.delete(event.code);
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
    };
  }, []);

  useFrame(({ camera }, delta) => {
    direction.set(0, 0, 0);
    camera.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();
    right.crossVectors(forward, camera.up).normalize();
    if (keys.current.has('KeyW')) direction.add(forward);
    if (keys.current.has('KeyS')) direction.sub(forward);
    if (keys.current.has('KeyD')) direction.add(right);
    if (keys.current.has('KeyA')) direction.sub(right);
    if (direction.lengthSq() > 0) {
      direction.normalize().multiplyScalar(Math.min(delta, .05) * 8);
      camera.position.add(direction);
      camera.position.y = 4.2;
      camera.position.x = THREE.MathUtils.clamp(camera.position.x, -72, 72);
      camera.position.z = THREE.MathUtils.clamp(camera.position.z, -72, 72);
    }
  });
  return null;
}

function TownScene({ world, preset }: { world: TownWorldState; preset: GraphicsPreset }) {
  const quality = GRAPHICS_PRESETS[preset];
  const night = world.environment.timeOfDay < 6 || world.environment.timeOfDay > 18;
  return (
    <>
      <color attach="background" args={[night ? '#020609' : '#0b2027']} />
      <fog attach="fog" args={[night ? '#03090c' : '#10252a', 38, preset === 'lite' ? 92 : 135]} />
      <ambientLight intensity={night ? .34 : .75} color="#a9d8d2" />
      <directionalLight
        position={[18, 32, 14]}
        intensity={night ? 1.2 : 2.8}
        color={night ? '#78b8ff' : '#fff0cf'}
        castShadow={quality.shadows}
        shadow-mapSize-width={preset === 'cinematic' ? 2048 : 1024}
        shadow-mapSize-height={preset === 'cinematic' ? 2048 : 1024}
      />
      <pointLight position={[0, 15, -18]} intensity={18} distance={48} color="#d6ad55" />
      <pointLight position={[0, 10, 0]} intensity={15} distance={38} color="#35f2d0" />

      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[180, 180]} />
        <meshStandardMaterial color="#050b0e" metalness={.18} roughness={.92} />
      </mesh>
      <gridHelper args={[180, 90, '#1b8d7c', '#0b2927']} position={[0, .01, 0]} />
      <Roads />
      {world.districts.map((district) => <DistrictBuilding key={district.id} district={district} />)}
      <TownHallInterior />
      {world.agents.slice(0, quality.avatarLimit).map((agent, index) => (
        <AgentAvatar key={agent.agentId} agent={agent} index={index} />
      ))}
      {world.activity.slice(0, quality.trafficLimit).map((flow, index) => (
        <DataFlow key={flow.id} flow={flow} index={index} />
      ))}
      <FirstPersonMovement />
      <PointerLockControls selector="#mc3d-enter-world" />
    </>
  );
}

export default function Town3DRenderer({ world, preset, onExit }: RendererProps) {
  const quality = GRAPHICS_PRESETS[preset];
  return (
    <div className="mc3d-renderer">
      <Canvas
        shadows={quality.shadows}
        dpr={[1, quality.pixelRatioCap]}
        camera={{ position: [0, 4.2, 48], fov: 62, near: .1, far: 240 }}
        gl={{ antialias: preset !== 'lite', powerPreference: 'high-performance' }}
        fallback={<div className="mc3d-no-webgl">WebGL unavailable. Returning to Command Town fallback.</div>}
      >
        <Suspense fallback={null}>
          <TownScene world={world} preset={preset} />
        </Suspense>
      </Canvas>
      <div className="mc3d-overlay">
        <div>
          <small>SP-MC3D-001 / {preset.toUpperCase()}</small>
          <strong>COMMAND TOWN 3D</strong>
          <span>WASD/mouse movement is renderer-local. Interaction remains projection-only.</span>
        </div>
        <div className="mc3d-actions">
          <button id="mc3d-enter-world" type="button">ENTER WORLD</button>
          <button type="button" onClick={onExit}>EXIT 3D</button>
        </div>
      </div>
      <div className="mc3d-authority">OBSERVATION LAYER · NO EXECUTION AUTHORITY</div>
    </div>
  );
}
