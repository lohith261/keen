export const vertexShader = `
  varying vec2 vUv;
  varying float vElevation;
  uniform float uTime;
  uniform float uScrollProgress;

  void main() {
    vUv = uv;

    vec3 pos = position;
    float wave1 = sin(pos.x * 2.0 + uTime * 0.3) * 0.15;
    float wave2 = sin(pos.y * 3.0 + uTime * 0.2) * 0.1;
    float wave3 = cos(pos.x * 1.5 + pos.y * 2.0 + uTime * 0.15) * 0.12;

    pos.z += (wave1 + wave2 + wave3) * (1.0 + uScrollProgress * 0.5);
    vElevation = pos.z;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

export const fragmentShader = `
  varying vec2 vUv;
  varying float vElevation;
  uniform float uTime;
  uniform float uScrollProgress;
  uniform vec2 uMouse;
  uniform float uTheme;

  vec3 darkPalette(float t) {
    vec3 a = vec3(0.02, 0.02, 0.03);
    vec3 b = vec3(0.08, 0.04, 0.01);
    vec3 c = vec3(1.0, 0.5, 0.2);
    vec3 d = vec3(0.0, 0.15, 0.2);
    return a + b * cos(6.28318 * (c * t + d));
  }

  vec3 lightPalette(float t) {
    vec3 a = vec3(0.92, 0.90, 0.87);
    vec3 b = vec3(0.06, 0.04, 0.02);
    vec3 c = vec3(1.0, 0.5, 0.2);
    vec3 d = vec3(0.0, 0.15, 0.2);
    return a + b * cos(6.28318 * (c * t + d));
  }

  void main() {
    vec2 uv = vUv;

    float dist = length(uv - vec2(0.5));
    float mouseDist = length(uv - uMouse);

    float noise1 = sin(uv.x * 8.0 + uTime * 0.2) * cos(uv.y * 6.0 + uTime * 0.15);
    float noise2 = sin(uv.x * 12.0 - uTime * 0.1) * sin(uv.y * 10.0 + uTime * 0.25);
    float noise3 = cos((uv.x + uv.y) * 5.0 + uTime * 0.18);

    float pattern = noise1 * 0.3 + noise2 * 0.2 + noise3 * 0.2;
    pattern += vElevation * 2.0;

    float mouseGlow = smoothstep(0.4, 0.0, mouseDist) * 0.15;

    float scrollBlend = uScrollProgress;

    vec3 dark1 = darkPalette(pattern + uTime * 0.05);
    vec3 dark2 = darkPalette(pattern + 0.5 + uTime * 0.03);
    vec3 darkColor = mix(dark1, dark2, scrollBlend);
    darkColor += vec3(0.9, 0.4, 0.1) * mouseGlow;
    darkColor *= 1.0 - dist * 0.6;

    vec3 light1 = lightPalette(pattern + uTime * 0.05);
    vec3 light2 = lightPalette(pattern + 0.5 + uTime * 0.03);
    vec3 lightColor = mix(light1, light2, scrollBlend);
    lightColor += vec3(0.9, 0.4, 0.1) * mouseGlow * 0.4;
    lightColor *= 1.0 - dist * 0.15;

    vec3 color = mix(darkColor, lightColor, uTheme);

    float gridAlpha = mix(0.03, 0.015, uTheme);
    float gridX = smoothstep(0.97, 1.0, abs(sin(uv.x * 40.0)));
    float gridY = smoothstep(0.97, 1.0, abs(sin(uv.y * 40.0)));
    float grid = max(gridX, gridY) * gridAlpha * (1.0 - scrollBlend * 0.5);
    color += vec3(grid);

    float alpha = mix(0.85, 0.5, uTheme);
    gl_FragColor = vec4(color, alpha);
  }
`;

export const particleVertexShader = `
  attribute float aScale;
  attribute float aSpeed;
  attribute float aOffset;
  uniform float uTime;
  uniform float uScrollProgress;
  varying float vAlpha;
  varying float vScale;

  void main() {
    vec3 pos = position;

    pos.y += mod(uTime * aSpeed * 0.1 + aOffset, 4.0) - 2.0;
    pos.x += sin(uTime * aSpeed * 0.2 + aOffset) * 0.3;
    pos.z += cos(uTime * aSpeed * 0.15 + aOffset) * 0.2;

    pos.y -= uScrollProgress * 2.0;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    float size = aScale * 3.0 * (1.0 + sin(uTime * aSpeed + aOffset) * 0.3);
    gl_PointSize = size * (300.0 / -mvPosition.z);

    vAlpha = 0.3 + sin(uTime * aSpeed * 0.5 + aOffset) * 0.2;
    vAlpha *= smoothstep(2.0, 0.5, abs(pos.y));
    vScale = aScale;
  }
`;

export const particleFragmentShader = `
  varying float vAlpha;
  varying float vScale;
  uniform float uTheme;

  void main() {
    float d = length(gl_PointCoord - vec2(0.5));
    float alpha = smoothstep(0.5, 0.1, d) * vAlpha;

    vec3 darkColor = mix(vec3(0.9, 0.4, 0.1), vec3(1.0, 0.7, 0.3), vScale);
    vec3 lightColor = mix(vec3(0.85, 0.35, 0.05), vec3(0.7, 0.4, 0.15), vScale);
    vec3 color = mix(darkColor, lightColor, uTheme);

    alpha *= mix(1.0, 0.5, uTheme);

    gl_FragColor = vec4(color, alpha);
  }
`;
