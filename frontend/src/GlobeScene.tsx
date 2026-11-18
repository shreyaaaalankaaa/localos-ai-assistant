import { Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, useTexture } from '@react-three/drei';
import * as THREE from 'three';

function Planet({ active }: { active: boolean }) {
  const earth = useRef<THREE.Group>(null);
  const [surface, lights, clouds] = useTexture([
    './textures/earth-silver.jpg',
    './textures/earth-lights.jpg',
    './textures/earth-clouds.png',
  ]);
  surface.colorSpace = THREE.SRGBColorSpace;
  lights.colorSpace = THREE.SRGBColorSpace;
  clouds.colorSpace = THREE.SRGBColorSpace;
  useFrame((_state, delta) => {
    if (earth.current) {
      earth.current.rotation.y += delta * (active ? 0.018 : 0.009);
    }
  });
  return (
    <group ref={earth} rotation={[0.07, -0.18, 0]}>
      <mesh>
        <sphereGeometry args={[1.76, 96, 64]} />
        <meshStandardMaterial
          map={surface}
          emissiveMap={lights}
          emissive="#ffffff"
          emissiveIntensity={1.6}
          metalness={0.03}
          roughness={0.93}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[1.775, 96, 64]} />
        <meshStandardMaterial
          map={clouds}
          transparent
          opacity={0.29}
          depthWrite={false}
          roughness={1}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      {/* Low-opacity Fresnel atmosphere, faint enough to preserve reference's black background. */}
      <mesh>
        <sphereGeometry args={[1.805, 80, 64]} />
        <shaderMaterial
          transparent
          side={THREE.BackSide}
          depthWrite={false}
          uniforms={{ glowColor: { value: new THREE.Color('#d8dce1') } }}
          vertexShader={`varying vec3 vNormal;varying vec3 vPosition;void main(){vNormal=normalize(normalMatrix*normal);vec4 world=modelViewMatrix*vec4(position,1.0);vPosition=world.xyz;gl_Position=projectionMatrix*world;}`}
          fragmentShader={`uniform vec3 glowColor;varying vec3 vNormal;varying vec3 vPosition;void main(){float rim=pow(1.0-abs(dot(normalize(vNormal),normalize(-vPosition))),3.0);gl_FragColor=vec4(glowColor,rim*0.29);}`}
        />
      </mesh>
    </group>
  );
}

export default function GlobeScene({ active = false }: { active?: boolean }) {
  return (
    <Canvas
      camera={{ position: [0, 0, 5.38], fov: 41, near: 0.1, far: 100 }}
      dpr={[1, 1.8]}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      style={{ background: 'transparent' }}
      aria-label="Interactive rotating Earth model. Drag to rotate."
    >
      <ambientLight intensity={0.37} />
      <hemisphereLight args={['#ffffff', '#202329', 0.5]} />
      <directionalLight position={[3.8, 3.2, 6]} color="#ffffff" intensity={2.3} />
      <directionalLight position={[-5, -2, -3]} color="#a6acb5" intensity={0.4} />
      <Suspense fallback={null}><Planet active={active} /></Suspense>
      <OrbitControls
        enableZoom={true}
        minDistance={4.3}
        maxDistance={7.4}
        enablePan={false}
        enableDamping={true}
        dampingFactor={0.06}
        rotateSpeed={0.5}
      />
    </Canvas>
  );
}
