/**
 * Canvas rendering utilities for the simulation using actual game images
 * Enhanced with particle effects, shadows, and visual polish
 */

import type { EntityData } from '../types/simulation';
import { ImageLoader } from './ImageLoader';
import { getFishPath, getEyePosition, type FishParams } from './fishTemplates';

// Animation constants
const IMAGE_CHANGE_RATE = 500; // milliseconds

// Particle system constants
const PARTICLE_COUNT = 30;
const PARTICLE_SIZE_MIN = 1;
const PARTICLE_SIZE_RANGE = 3;
const PARTICLE_SPEED_MIN = 0.1;
const PARTICLE_SPEED_RANGE = 0.3;
const PARTICLE_OPACITY_MIN = 0.1;
const PARTICLE_OPACITY_RANGE = 0.4;
const PARTICLE_WOBBLE_INCREMENT = 0.02;
const PARTICLE_WOBBLE_AMPLITUDE = 0.5;
const PARTICLE_BOUNDS_MARGIN = 10;

// Background gradient stops
const GRADIENT_STOP_1 = 0.3;
const GRADIENT_STOP_2 = 0.6;

// Light ray constants
const LIGHT_RAY_COUNT = 4;
const LIGHT_RAY_OPACITY_MAIN = 0.08;
const LIGHT_RAY_OPACITY_SECONDARY = 0.15;
const CAUSTICS_SPEED = 0.0005;
const CAUSTICS_AMPLITUDE = 30;
const WOBBLE_SPEED = 0.0003;
const WOBBLE_AMPLITUDE = 15;

// Seabed constants
const SEABED_MIN_HEIGHT = 50;
const SEABED_HEIGHT_RATIO = 0.12;
const SEABED_TEXTURE_SPACING = 40;
const SEABED_ROCK_SIZE_MIN = 4;
const SEABED_ROCK_SIZE_RANGE = 8;
const SEABED_TEXTURE_OPACITY = 0.2;

// Particle highlight constants
const PARTICLE_HIGHLIGHT_OPACITY_MULTIPLIER = 0.6;
const PARTICLE_HIGHLIGHT_OFFSET_RATIO = 0.3;
const PARTICLE_HIGHLIGHT_SIZE_RATIO = 0.4;

// Food type image mappings (matching core/constants.py)
const FOOD_TYPE_IMAGES: Record<string, string[]> = {
  algae: ['food_algae1.png', 'food_algae2.png'],
  protein: ['food_protein1.png', 'food_protein2.png'],
  energy: ['food_energy1.png', 'food_energy2.png'],
  rare: ['food_rare1.png', 'food_rare2.png'],
  nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
  live: ['food_energy1.png', 'food_energy2.png'], // Live food uses energy images but with special effects
};

// Default food images for unknown types
const DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

// Default fish images for fallback rendering
const DEFAULT_FISH_IMAGES = ['george1.png', 'george2.png'];

// Particle system for ambient water effects
interface Particle {
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
  wobble: number;
}

export class Renderer {
  private ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private initialized = false;

  constructor(ctx: CanvasRenderingContext2D) {
    this.ctx = ctx;
  }

  private initParticles() {
    if (this.initialized) return;
    this.initialized = true;

    // Create ambient floating particles (bubbles, debris)
    const width = this.ctx.canvas.width;
    const height = this.ctx.canvas.height;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      this.particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * PARTICLE_SIZE_RANGE + PARTICLE_SIZE_MIN,
        speed: Math.random() * PARTICLE_SPEED_RANGE + PARTICLE_SPEED_MIN,
        opacity: Math.random() * PARTICLE_OPACITY_RANGE + PARTICLE_OPACITY_MIN,
        wobble: Math.random() * Math.PI * 2,
      });
    }
  }

  clear(width: number, height: number) {
    this.initParticles();
    const time = Date.now();

    // Enhanced ocean gradient with more depth
    const gradient = this.ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, '#051d35');
    gradient.addColorStop(GRADIENT_STOP_1, '#0a3854');
    gradient.addColorStop(GRADIENT_STOP_2, '#0d4a6b');
    gradient.addColorStop(1, '#0e2838');
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(0, 0, width, height);

    // Animated light rays with caustics effect
    this.ctx.save();
    const causticsOffset = Math.sin(time * CAUSTICS_SPEED) * CAUSTICS_AMPLITUDE;
    for (let i = 0; i < LIGHT_RAY_COUNT; i += 1) {
      const baseX = (width / LIGHT_RAY_COUNT) * i + causticsOffset;
      const wobble = Math.sin(time * WOBBLE_SPEED + i) * WOBBLE_AMPLITUDE;

      // Main light ray
      this.ctx.globalAlpha = LIGHT_RAY_OPACITY_MAIN;
      this.ctx.beginPath();
      this.ctx.moveTo(baseX + 60 + wobble, 0);
      this.ctx.lineTo(baseX + 180 + wobble, 0);
      this.ctx.lineTo(baseX + wobble, height);
      this.ctx.closePath();
      const rayGradient = this.ctx.createLinearGradient(baseX, 0, baseX, height);
      rayGradient.addColorStop(0, '#4dd5ff');
      rayGradient.addColorStop(0.6, '#3dd5ff');
      rayGradient.addColorStop(1, 'rgba(61, 213, 255, 0)');
      this.ctx.fillStyle = rayGradient;
      this.ctx.fill();

      // Secondary highlight for caustics
      this.ctx.globalAlpha = LIGHT_RAY_OPACITY_SECONDARY;
      this.ctx.beginPath();
      this.ctx.moveTo(baseX + 80 + wobble * 1.5, 0);
      this.ctx.lineTo(baseX + 120 + wobble * 1.5, 0);
      this.ctx.lineTo(baseX + 40 + wobble, height * 0.4);
      this.ctx.closePath();
      this.ctx.fillStyle = '#5de5ff';
      this.ctx.fill();
    }
    this.ctx.restore();

    // Update and draw floating particles
    this.updateParticles(width, height);
    this.drawParticles();

    // Enhanced seabed with texture
    const seabedHeight = Math.max(SEABED_MIN_HEIGHT, height * SEABED_HEIGHT_RATIO);
    const seabedY = height - seabedHeight;

    // Seabed gradient with more depth
    const seabedGradient = this.ctx.createLinearGradient(0, seabedY, 0, height);
    seabedGradient.addColorStop(0, 'rgba(180, 145, 85, 0.15)');
    seabedGradient.addColorStop(0.5, 'rgba(200, 160, 95, 0.3)');
    seabedGradient.addColorStop(1, 'rgba(160, 130, 75, 0.4)');
    this.ctx.fillStyle = seabedGradient;
    this.ctx.fillRect(0, seabedY, width, seabedHeight);

    // Add seabed texture (rocks/pebbles)
    this.ctx.save();
    this.ctx.globalAlpha = SEABED_TEXTURE_OPACITY;
    for (let x = 0; x < width; x += SEABED_TEXTURE_SPACING) {
      const rockSize = Math.random() * SEABED_ROCK_SIZE_RANGE + SEABED_ROCK_SIZE_MIN;
      const rockX = x + Math.random() * 30;
      const rockY = seabedY + seabedHeight * 0.6 + Math.random() * 15;
      this.ctx.fillStyle = '#8b6f47';
      this.ctx.beginPath();
      this.ctx.ellipse(rockX, rockY, rockSize, rockSize * 0.7, 0, 0, Math.PI * 2);
      this.ctx.fill();
    }
    this.ctx.restore();
  }

  private updateParticles(width: number, height: number) {
    for (const particle of this.particles) {
      // Float upward
      particle.y -= particle.speed;

      // Wobble side to side
      particle.wobble += PARTICLE_WOBBLE_INCREMENT;
      particle.x += Math.sin(particle.wobble) * PARTICLE_WOBBLE_AMPLITUDE;

      // Reset if out of bounds
      if (particle.y < -PARTICLE_BOUNDS_MARGIN) {
        particle.y = height + PARTICLE_BOUNDS_MARGIN;
        particle.x = Math.random() * width;
      }
      if (particle.x < -PARTICLE_BOUNDS_MARGIN) particle.x = width + PARTICLE_BOUNDS_MARGIN;
      if (particle.x > width + PARTICLE_BOUNDS_MARGIN) particle.x = -PARTICLE_BOUNDS_MARGIN;
    }
  }

  private drawParticles() {
    this.ctx.save();
    for (const particle of this.particles) {
      this.ctx.globalAlpha = particle.opacity;
      this.ctx.fillStyle = '#8dd5ef';

      // Draw bubble with highlight
      this.ctx.beginPath();
      this.ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      this.ctx.fill();

      // Highlight
      this.ctx.globalAlpha = particle.opacity * PARTICLE_HIGHLIGHT_OPACITY_MULTIPLIER;
      this.ctx.fillStyle = '#ffffff';
      this.ctx.beginPath();
      this.ctx.arc(
        particle.x - particle.size * PARTICLE_HIGHLIGHT_OFFSET_RATIO,
        particle.y - particle.size * PARTICLE_HIGHLIGHT_OFFSET_RATIO,
        particle.size * PARTICLE_HIGHLIGHT_SIZE_RATIO,
        0,
        Math.PI * 2
      );
      this.ctx.fill();
    }
    this.ctx.restore();
  }

  renderEntity(entity: EntityData, elapsedTime: number) {
    switch (entity.type) {
      case 'fish':
        this.renderFish(entity, elapsedTime);
        break;
      case 'food':
        this.renderFood(entity, elapsedTime);
        break;
      case 'plant':
        this.renderPlant(entity, elapsedTime);
        break;
      case 'crab':
        this.renderCrab(entity, elapsedTime);
        break;
      case 'castle':
        this.renderCastle(entity);
        break;
      case 'jellyfish':
        this.renderJellyfish(entity, elapsedTime);
        break;
    }
  }

  private renderFish(fish: EntityData, elapsedTime: number) {
    const { ctx } = this;
    const { x, y, width, height, vel_x = 1, genome_data } = fish;

    // Use SVG-based parametric fish rendering if genome_data is available
    if (genome_data && genome_data.template_id !== undefined) {
      this.renderSVGFish(fish);
      return;
    }

    // Fallback to image-based rendering for backward compatibility
    const imageIndex = this.getAnimationFrame(elapsedTime, DEFAULT_FISH_IMAGES.length);
    const imageName = DEFAULT_FISH_IMAGES[imageIndex];
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    const sizeModifier = genome_data?.size || 1.0;
    const scaledWidth = width * sizeModifier;
    const scaledHeight = height * sizeModifier;
    const flipHorizontal = vel_x < 0;

    this.drawShadow(x + scaledWidth / 2, y + scaledHeight, scaledWidth * 0.8, scaledHeight * 0.3);

    const energy = fish.energy !== undefined ? fish.energy : 100;
    if (energy > 70) {
      this.drawGlow(x + scaledWidth / 2, y + scaledHeight / 2, scaledWidth * 0.7, energy);
    }

    ctx.save();
    if (genome_data?.color_hue !== undefined) {
      this.drawImageWithColorTint(image, x, y, scaledWidth, scaledHeight, flipHorizontal, genome_data.color_hue);
    } else {
      this.drawImage(image, x, y, scaledWidth, scaledHeight, flipHorizontal);
    }
    ctx.restore();

    if (fish.energy !== undefined) {
      this.drawEnhancedEnergyBar(x, y - 12, scaledWidth, fish.energy);
    }
  }

  private renderSVGFish(fish: EntityData) {
    const { ctx } = this;
    const { x, y, width, height, vel_x = 1, genome_data } = fish;

    if (!genome_data) return;

    // Prepare fish parameters
    const fishParams: FishParams = {
      fin_size: genome_data.fin_size || 1.0,
      tail_size: genome_data.tail_size || 1.0,
      body_aspect: genome_data.body_aspect || 1.0,
      eye_size: genome_data.eye_size || 1.0,
      pattern_intensity: genome_data.pattern_intensity || 0.5,
      pattern_type: genome_data.pattern_type || 0,
      color_hue: genome_data.color_hue || 0.5,
      size: genome_data.size || 1.0,
      template_id: genome_data.template_id || 0,
    };

    // Calculate fish dimensions
    const baseSize = Math.max(width, height);
    const sizeModifier = fishParams.size;
    const scaledSize = baseSize * sizeModifier;

    // Flip based on velocity direction
    const flipHorizontal = vel_x < 0;

    // Draw soft shadow
    this.drawShadow(x + scaledSize / 2, y + scaledSize, scaledSize * 0.8, scaledSize * 0.3);

    // Draw glow effect based on energy
    const energy = fish.energy !== undefined ? fish.energy : 100;
    if (energy > 70) {
      this.drawGlow(x + scaledSize / 2, y + scaledSize / 2, scaledSize * 0.7, energy);
    }

    ctx.save();

    // Position and flip
    ctx.translate(x + scaledSize / 2, y + scaledSize / 2);
    if (flipHorizontal) {
      ctx.scale(-1, 1);
    }
    ctx.translate(-scaledSize / 2, -scaledSize / 2);

    // Get base color from hue
    const baseColor = this.hslToRgbString(fishParams.color_hue, 0.7, 0.6);
    const patternColor = this.hslToRgbString(fishParams.color_hue, 0.8, 0.3);

    // Get SVG path for the fish body
    const fishPath = getFishPath(fishParams, scaledSize);

    // Draw fish body
    const path = new Path2D(fishPath);

    // Fill with base color
    ctx.fillStyle = baseColor;
    ctx.fill(path);

    // Stroke outline
    ctx.strokeStyle = this.hslToRgbString(fishParams.color_hue, 0.8, 0.4);
    ctx.lineWidth = 1.5;
    ctx.stroke(path);

    // Draw pattern if applicable
    if (fishParams.pattern_intensity > 0.1) {
      this.drawFishPattern(fishParams, scaledSize, patternColor);
    }

    // Draw eye
    const eyePos = getEyePosition(fishParams, scaledSize);
    const eyeRadius = 3 * fishParams.eye_size;

    // Eye white
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(eyePos.x, eyePos.y, eyeRadius, 0, Math.PI * 2);
    ctx.fill();

    // Eye pupil
    ctx.fillStyle = 'black';
    ctx.beginPath();
    ctx.arc(eyePos.x, eyePos.y, eyeRadius * 0.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();

    // Draw enhanced energy bar
    if (fish.energy !== undefined) {
      this.drawEnhancedEnergyBar(x, y - 12, scaledSize, fish.energy);
    }
  }

  private drawFishPattern(params: FishParams, baseSize: number, color: string) {
    const { ctx } = this;
    const width = baseSize * params.body_aspect;
    const height = baseSize;
    const opacity = params.pattern_intensity * 0.4;

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;

    switch (params.pattern_type) {
      case 0: // Stripes
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(width * 0.3, height * 0.2);
        ctx.lineTo(width * 0.3, height * 0.8);
        ctx.moveTo(width * 0.5, height * 0.2);
        ctx.lineTo(width * 0.5, height * 0.8);
        ctx.moveTo(width * 0.7, height * 0.2);
        ctx.lineTo(width * 0.7, height * 0.8);
        ctx.stroke();
        break;

      case 1: // Spots
        [
          { x: width * 0.4, y: height * 0.35 },
          { x: width * 0.6, y: height * 0.4 },
          { x: width * 0.5, y: height * 0.6 },
          { x: width * 0.7, y: height * 0.65 },
        ].forEach(spot => {
          ctx.beginPath();
          ctx.arc(spot.x, spot.y, 3, 0, Math.PI * 2);
          ctx.fill();
        });
        break;

      case 2: // Solid (darker overlay)
        const path = new Path2D(getFishPath(params, baseSize));
        ctx.globalAlpha = opacity * 0.5;
        ctx.fill(path);
        break;

      case 3: // Gradient
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        const gradPath = new Path2D(getFishPath(params, baseSize));
        ctx.fill(gradPath);
        break;
    }

    ctx.restore();
  }

  private hslToRgbString(h: number, s: number, l: number): string {
    const rgb = this.hslToRgb(h, s, l);
    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
  }

  private drawShadow(x: number, y: number, width: number, height: number) {
    const { ctx } = this;
    ctx.save();
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.ellipse(x, y, width / 2, height / 2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  private drawGlow(x: number, y: number, size: number, energy: number) {
    const { ctx } = this;
    const intensity = (energy - 70) / 30; // 0 to 1 for energy 70-100

    ctx.save();
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
    gradient.addColorStop(0, `rgba(100, 220, 255, ${0.15 * intensity})`);
    gradient.addColorStop(0.5, `rgba(80, 200, 240, ${0.08 * intensity})`);
    gradient.addColorStop(1, 'rgba(60, 180, 220, 0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  private renderFood(food: EntityData, elapsedTime: number) {
    const { x, y, width, height, food_type } = food;

    // Get animation frames for this food type
    const imageFiles = food_type
      ? FOOD_TYPE_IMAGES[food_type] || DEFAULT_FOOD_IMAGES
      : DEFAULT_FOOD_IMAGES;
    const imageIndex = this.getAnimationFrame(elapsedTime, imageFiles.length);
    const imageName = imageFiles[imageIndex];
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    // Make food images smaller (0.7x scale for normal food, 0.35x for live food)
    const isLiveFood = food_type === 'live';
    const foodScale = isLiveFood ? 0.35 : 0.7;
    const scaledWidth = width * foodScale;
    const scaledHeight = height * foodScale;
    // Center the smaller food at original position
    const offsetX = (width - scaledWidth) / 2;
    const offsetY = (height - scaledHeight) / 2;

    // Draw subtle shadow
    this.drawShadow(x + width / 2, y + height, scaledWidth * 0.6, scaledHeight * 0.2);

    // Live food gets special visual treatment
    if (isLiveFood) {
      // Pulsing animation for live food
      const pulse = Math.sin(elapsedTime * 0.005) * 0.3 + 0.7;
      const cx = x + width / 2;
      const cy = y + height / 2;
      const planktonSeed = (x + y) * 0.01;

      // Simple translucent body for zooplankton
      this.ctx.save();
      this.ctx.globalAlpha = 0.4 * pulse;
      const bodyGlow = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, scaledWidth * 0.8);
      bodyGlow.addColorStop(0, '#aaffff');
      bodyGlow.addColorStop(0.6, '#6ad8d8');
      bodyGlow.addColorStop(1, 'rgba(106, 216, 216, 0)');
      this.ctx.fillStyle = bodyGlow;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, scaledWidth * 0.8, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();

      // Simple appendages for zooplankton (4 appendages)
      this.ctx.save();
      this.ctx.lineWidth = 0.8;
      this.ctx.strokeStyle = `rgba(140, 220, 240, ${0.35 * pulse})`;
      for (let i = 0; i < 4; i++) {
        const angle = (Math.PI * 2 * i) / 4 + pulse * 0.3;
        const sway = Math.sin(elapsedTime * 0.003 + planktonSeed + i) * 2;
        const length = scaledWidth * 0.5;
        const startX = cx + Math.cos(angle) * (scaledWidth * 0.3);
        const startY = cy + Math.sin(angle) * (scaledWidth * 0.3);
        const endX = cx + Math.cos(angle) * length + sway;
        const endY = cy + Math.sin(angle) * length + sway * 0.5;

        this.ctx.beginPath();
        this.ctx.moveTo(startX, startY);
        this.ctx.lineTo(endX, endY);
        this.ctx.stroke();
      }
      this.ctx.restore();

      // Simple central highlight
      this.ctx.save();
      this.ctx.fillStyle = `rgba(255, 255, 255, ${0.4 * pulse})`;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, scaledWidth * 0.15, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();
    } else {
      // Normal food gets subtle glow
      this.ctx.save();
      this.ctx.globalAlpha = 0.2;
      const gradient = this.ctx.createRadialGradient(
        x + width / 2,
        y + height / 2,
        0,
        x + width / 2,
        y + height / 2,
        scaledWidth * 0.6
      );
      gradient.addColorStop(0, '#ffeb3b');
      gradient.addColorStop(1, 'rgba(255, 235, 59, 0)');
      this.ctx.fillStyle = gradient;
      this.ctx.beginPath();
      this.ctx.arc(x + width / 2, y + height / 2, scaledWidth * 0.6, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();
    }

    // Food images don't flip
    this.drawImage(image, x + offsetX, y + offsetY, scaledWidth, scaledHeight, false);
  }

  private renderPlant(plant: EntityData, elapsedTime: number) {
    const { ctx } = this;
    const { x, y, width, height, plant_type = 1 } = plant;

    // Get plant image (plant_type is 1 or 2)
    const imageName = plant_type === 1 ? 'plant1-improved.png' : 'plant2.png';
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    // Make plant images 100% larger (2x scale)
    const plantScale = 2.0;
    const scaledWidth = width * plantScale;
    const scaledHeight = height * plantScale;

    ctx.save();
    const canvasHeight = ctx.canvas.height;
    const seabedOffset = Math.max(40, canvasHeight * 0.08);
    const restingY = canvasHeight - seabedOffset;

    // Enhanced multi-frequency swaying for organic motion
    const plantSeed = x + y; // Unique seed per plant
    const primarySway = Math.sin(elapsedTime * 0.0005 + plantSeed * 0.01) * 6;
    const secondarySway = Math.sin(elapsedTime * 0.0012 + plantSeed * 0.02) * 3;
    const tertiarySway = Math.sin(elapsedTime * 0.0008 + plantSeed * 0.015) * 2;
    const swayAngle = primarySway + secondarySway + tertiarySway;

    // Horizontal sway offset for more natural movement
    const swayOffset = Math.sin(elapsedTime * 0.0006 + plantSeed * 0.01) * 8;

    // Position setup
    const centerX = x + scaledWidth / 2 + swayOffset;
    const centerY = restingY;

    // Draw shadow for depth
    ctx.globalAlpha = 0.3;
    ctx.fillStyle = 'rgba(0, 20, 40, 0.4)';
    ctx.beginPath();
    ctx.ellipse(
      centerX,
      restingY + 5,
      scaledWidth * 0.4,
      scaledHeight * 0.1,
      0,
      0,
      Math.PI * 2
    );
    ctx.fill();
    ctx.globalAlpha = 1.0;

    // Add subtle glow effect
    const glowIntensity = 0.15 + Math.sin(elapsedTime * 0.001 + plantSeed) * 0.05;
    ctx.shadowColor = plant_type === 1 ? 'rgba(100, 200, 150, 0.4)' : 'rgba(150, 100, 200, 0.4)';
    ctx.shadowBlur = 15 * glowIntensity;

    // Apply color tinting based on shimmer
    const shimmer = 1.0 + Math.sin(elapsedTime * 0.0015 + plantSeed * 0.03) * 0.08;
    ctx.filter = `brightness(${shimmer}) saturate(1.1)`;

    // Apply transformation and draw plant
    ctx.translate(centerX, centerY);
    ctx.rotate((swayAngle * Math.PI) / 180);
    ctx.drawImage(image, -scaledWidth / 2, -scaledHeight, scaledWidth, scaledHeight);

    ctx.restore();

    // Draw occasional bubbles rising from plants
    this.renderPlantBubbles(plant, elapsedTime, centerX, restingY - scaledHeight * 0.7);
  }

  private renderPlantBubbles(plant: EntityData, elapsedTime: number, x: number, y: number) {
    const { ctx } = this;
    const plantSeed = (plant.x || 0) + (plant.y || 0);

    // Each plant produces 2-3 bubbles at different intervals
    for (let i = 0; i < 3; i++) {
      const bubblePhase = (elapsedTime * 0.0008 + plantSeed * 0.1 + i * 2.1) % 6.28; // 0 to 2π
      const bubbleActive = bubblePhase < 4.0; // Bubble exists for part of cycle

      if (!bubbleActive) continue;

      // Bubble rises and drifts
      const riseProgress = bubblePhase / 4.0;
      const bubbleY = y - riseProgress * 80;
      const bubbleX = x + Math.sin(bubblePhase * 3 + i) * 15;
      const bubbleSize = (2 + i * 0.5) * (1 - riseProgress * 0.3); // Shrink slightly as it rises

      // Fade out as bubble rises
      ctx.save();
      ctx.globalAlpha = Math.max(0, 1 - riseProgress);

      // Draw bubble
      const gradient = ctx.createRadialGradient(
        bubbleX - bubbleSize * 0.3,
        bubbleY - bubbleSize * 0.3,
        0,
        bubbleX,
        bubbleY,
        bubbleSize
      );
      gradient.addColorStop(0, 'rgba(200, 240, 255, 0.6)');
      gradient.addColorStop(0.5, 'rgba(150, 220, 255, 0.3)');
      gradient.addColorStop(1, 'rgba(100, 200, 255, 0.1)');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(bubbleX, bubbleY, bubbleSize, 0, Math.PI * 2);
      ctx.fill();

      // Add bubble highlight
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.beginPath();
      ctx.arc(bubbleX - bubbleSize * 0.3, bubbleY - bubbleSize * 0.3, bubbleSize * 0.3, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
  }

  private renderCrab(crab: EntityData, elapsedTime: number) {
    const { x, y, width, height, vel_x = 1 } = crab;

    // Get animation frames for crab
    const imageFiles = ['crab1.png', 'crab2.png'];
    const imageIndex = this.getAnimationFrame(elapsedTime, imageFiles.length);
    const imageName = imageFiles[imageIndex];
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    // Draw shadow
    this.drawShadow(x + width / 2, y + height, width * 0.7, height * 0.25);

    // Flip based on velocity
    const flipHorizontal = vel_x < 0;
    this.drawImage(image, x, y, width, height, flipHorizontal);
  }

  private renderJellyfish(jellyfish: EntityData, elapsedTime: number) {
    const { ctx } = this;
    const { x, y, width, height, energy = 1000 } = jellyfish;

    // Animation variables
    const pulse = Math.sin(elapsedTime * 0.002) * 0.1 + 0.9; // Pulsing animation
    const tentacleWave = elapsedTime * 0.003;

    ctx.save();

    // Center position
    const centerX = x + width / 2;
    const centerY = y + height / 3;

    // Draw translucent dome/bell
    const domeRadius = (width / 2) * pulse;
    const domeHeight = height / 2;

    // Dome gradient (semi-transparent purple/pink)
    const domeGradient = ctx.createRadialGradient(
      centerX,
      centerY - domeHeight * 0.3,
      0,
      centerX,
      centerY,
      domeRadius
    );
    domeGradient.addColorStop(0, 'rgba(200, 100, 255, 0.6)');
    domeGradient.addColorStop(0.5, 'rgba(150, 80, 220, 0.5)');
    domeGradient.addColorStop(1, 'rgba(100, 60, 180, 0.3)');

    // Draw dome
    ctx.fillStyle = domeGradient;
    ctx.beginPath();
    ctx.ellipse(centerX, centerY, domeRadius, domeHeight, 0, Math.PI, 0, true);
    ctx.fill();

    // Add dome highlight
    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.beginPath();
    ctx.ellipse(
      centerX - domeRadius * 0.3,
      centerY - domeHeight * 0.5,
      domeRadius * 0.4,
      domeHeight * 0.3,
      0,
      0,
      Math.PI * 2
    );
    ctx.fill();

    // Draw tentacles (4-6 wavy lines)
    const tentacleCount = 5;
    ctx.strokeStyle = 'rgba(150, 80, 220, 0.6)';
    ctx.lineWidth = 2;

    for (let i = 0; i < tentacleCount; i++) {
      const offsetX = ((i - tentacleCount / 2) / tentacleCount) * width * 0.8;
      const startX = centerX + offsetX;
      const startY = centerY + domeHeight * 0.5;

      ctx.beginPath();
      ctx.moveTo(startX, startY);

      // Draw wavy tentacle
      const segments = 6;
      for (let j = 1; j <= segments; j++) {
        const segmentY = startY + (j / segments) * height * 0.6;
        const waveOffset = Math.sin(tentacleWave + i + j * 0.5) * 5;
        ctx.lineTo(startX + waveOffset, segmentY);
      }
      ctx.stroke();
    }

    // Draw energy bar above jellyfish
    if (energy !== undefined) {
      this.drawEnhancedEnergyBar(x, y - 12, width, energy / 10); // Jellyfish has max 1000 energy
    }

    // Add glow effect
    ctx.shadowColor = 'rgba(150, 80, 220, 0.5)';
    ctx.shadowBlur = 15 * pulse;

    ctx.restore();
  }

  private renderCastle(castle: EntityData) {
    const { x, y, width, height } = castle;

    const imageName = 'castle-improved.png';
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    // Castles don't flip or animate
    this.drawImage(image, x, y, width, height, false);
  }

  private drawImage(
    image: HTMLImageElement,
    x: number,
    y: number,
    width: number,
    height: number,
    flipHorizontal: boolean
  ) {
    const { ctx } = this;

    if (flipHorizontal) {
      ctx.save();
      ctx.translate(x + width, y);
      ctx.scale(-1, 1);
      ctx.drawImage(image, 0, 0, width, height);
      ctx.restore();
    } else {
      ctx.drawImage(image, x, y, width, height);
    }
  }

  private drawImageWithColorTint(
    image: HTMLImageElement,
    x: number,
    y: number,
    width: number,
    height: number,
    flipHorizontal: boolean,
    colorHue: number
  ) {
    const { ctx } = this;

    // Create temporary canvas for color tinting
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = image.width;
    tempCanvas.height = image.height;
    const tempCtx = tempCanvas.getContext('2d');
    if (!tempCtx) return;

    // Draw original image
    if (flipHorizontal) {
      tempCtx.save();
      tempCtx.translate(tempCanvas.width, 0);
      tempCtx.scale(-1, 1);
      tempCtx.drawImage(image, 0, 0);
      tempCtx.restore();
    } else {
      tempCtx.drawImage(image, 0, 0);
    }

    // Apply color tint using multiply blend mode
    // Convert HSL color to RGB for genetic color trait
    const tintColor = this.hslToRgb(colorHue / 360, 0.7, 0.6);
    tempCtx.globalCompositeOperation = 'multiply';
    tempCtx.fillStyle = `rgb(${tintColor[0]}, ${tintColor[1]}, ${tintColor[2]})`;
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    // Restore original alpha
    tempCtx.globalCompositeOperation = 'destination-in';
    if (flipHorizontal) {
      tempCtx.save();
      tempCtx.translate(tempCanvas.width, 0);
      tempCtx.scale(-1, 1);
      tempCtx.drawImage(image, 0, 0);
      tempCtx.restore();
    } else {
      tempCtx.drawImage(image, 0, 0);
    }

    // Draw tinted image to main canvas
    ctx.drawImage(tempCanvas, x, y, width, height);
  }

  private hslToRgb(h: number, s: number, l: number): [number, number, number] {
    let r: number, g: number, b: number;

    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p: number, q: number, t: number) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
      };

      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1 / 3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1 / 3);
    }

    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
  }

  private drawEnhancedEnergyBar(x: number, y: number, width: number, energy: number) {
    const { ctx } = this;
    const barHeight = 6;
    const barWidth = width;
    const padding = 1;

    // Background with border
    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    const radius = 2;
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, barHeight, radius);
    ctx.fill();
    ctx.stroke();

    // Energy bar with gradient
    let colorStart: string, colorEnd: string, glowColor: string;
    if (energy < 30) {
      colorStart = '#ff6b6b';
      colorEnd = '#ef4444';
      glowColor = 'rgba(239, 68, 68, 0.5)';
    } else if (energy < 60) {
      colorStart = '#ffd93d';
      colorEnd = '#fbbf24';
      glowColor = 'rgba(251, 191, 36, 0.5)';
    } else {
      colorStart = '#6bffb8';
      colorEnd = '#4ade80';
      glowColor = 'rgba(74, 222, 128, 0.5)';
    }

    const barFillWidth = (barWidth - padding * 2) * (energy / 100);

    if (barFillWidth > 0) {
      // Glow effect
      ctx.shadowColor = glowColor;
      ctx.shadowBlur = 8;

      // Gradient fill
      const gradient = ctx.createLinearGradient(x, y, x + barFillWidth, y);
      gradient.addColorStop(0, colorStart);
      gradient.addColorStop(1, colorEnd);
      ctx.fillStyle = gradient;

      ctx.beginPath();
      ctx.roundRect(x + padding, y + padding, barFillWidth, barHeight - padding * 2, radius - 1);
      ctx.fill();

      // Highlight on top
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 0.4;
      const highlightGradient = ctx.createLinearGradient(x, y, x, y + barHeight / 2);
      highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
      highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlightGradient;
      ctx.fillRect(x + padding, y + padding, barFillWidth, barHeight / 3);
    }

    ctx.restore();
  }

  private getAnimationFrame(elapsedTime: number, frameCount: number): number {
    if (frameCount <= 1) return 0;
    return Math.floor(elapsedTime / IMAGE_CHANGE_RATE) % frameCount;
  }
}
