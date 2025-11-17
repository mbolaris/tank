/**
 * Canvas rendering utilities for the simulation using actual game images
 * Enhanced with particle effects, shadows, and visual polish
 */

import type { EntityData } from '../types/simulation';
import { ImageLoader } from './ImageLoader';

// Constants matching pygame version
const IMAGE_CHANGE_RATE = 500; // milliseconds

// Food type image mappings (matching core/constants.py)
const FOOD_TYPE_IMAGES: Record<string, string[]> = {
  algae: ['food_algae1.png', 'food_algae2.png'],
  protein: ['food_protein1.png', 'food_protein2.png'],
  energy: ['food_energy1.png', 'food_energy2.png'],
  rare: ['food_rare1.png', 'food_rare2.png'],
  nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
};

// Default food images for unknown types
const DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

// Fish species image mappings
const FISH_SPECIES_IMAGES: Record<string, string[]> = {
  solo: ['george1.png', 'george2.png'],
  algorithmic: ['george1.png', 'george2.png'],
  neural: ['george1.png', 'george2.png'],
  schooling: ['school.png'],
};

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

    for (let i = 0; i < 30; i++) {
      this.particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 3 + 1,
        speed: Math.random() * 0.3 + 0.1,
        opacity: Math.random() * 0.4 + 0.1,
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
    gradient.addColorStop(0.3, '#0a3854');
    gradient.addColorStop(0.6, '#0d4a6b');
    gradient.addColorStop(1, '#0e2838');
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(0, 0, width, height);

    // Animated light rays with caustics effect
    this.ctx.save();
    const causticsOffset = Math.sin(time * 0.0005) * 30;
    for (let i = 0; i < 4; i += 1) {
      const baseX = (width / 4) * i + causticsOffset;
      const wobble = Math.sin(time * 0.0003 + i) * 15;

      // Main light ray
      this.ctx.globalAlpha = 0.08;
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
      this.ctx.globalAlpha = 0.15;
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
    this.updateParticles(width, height, time);
    this.drawParticles();

    // Enhanced seabed with texture
    const seabedHeight = Math.max(50, height * 0.12);
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
    this.ctx.globalAlpha = 0.2;
    for (let x = 0; x < width; x += 40) {
      const rockSize = Math.random() * 8 + 4;
      const rockX = x + Math.random() * 30;
      const rockY = seabedY + seabedHeight * 0.6 + Math.random() * 15;
      this.ctx.fillStyle = '#8b6f47';
      this.ctx.beginPath();
      this.ctx.ellipse(rockX, rockY, rockSize, rockSize * 0.7, 0, 0, Math.PI * 2);
      this.ctx.fill();
    }
    this.ctx.restore();
  }

  private updateParticles(width: number, height: number, _time: number) {
    for (const particle of this.particles) {
      // Float upward
      particle.y -= particle.speed;

      // Wobble side to side
      particle.wobble += 0.02;
      particle.x += Math.sin(particle.wobble) * 0.5;

      // Reset if out of bounds
      if (particle.y < -10) {
        particle.y = height + 10;
        particle.x = Math.random() * width;
      }
      if (particle.x < -10) particle.x = width + 10;
      if (particle.x > width + 10) particle.x = -10;
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
      this.ctx.globalAlpha = particle.opacity * 0.6;
      this.ctx.fillStyle = '#ffffff';
      this.ctx.beginPath();
      this.ctx.arc(
        particle.x - particle.size * 0.3,
        particle.y - particle.size * 0.3,
        particle.size * 0.4,
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
        this.renderCastle(entity, elapsedTime);
        break;
    }
  }

  private renderFish(fish: EntityData, elapsedTime: number) {
    const { ctx } = this;
    const { x, y, width, height, species = 'solo', vel_x = 1, genome_data } = fish;

    // Get animation frames for this species
    const imageFiles = FISH_SPECIES_IMAGES[species] || FISH_SPECIES_IMAGES.solo;
    const imageIndex = this.getAnimationFrame(elapsedTime, imageFiles.length);
    const imageName = imageFiles[imageIndex];
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    // Calculate scale based on genome
    const sizeModifier = genome_data?.size || 1.0;
    const scaledWidth = width * sizeModifier;
    const scaledHeight = height * sizeModifier;

    // Flip image based on velocity direction
    const flipHorizontal = vel_x < 0;

    // Draw soft shadow
    this.drawShadow(x + scaledWidth / 2, y + scaledHeight, scaledWidth * 0.8, scaledHeight * 0.3);

    // Draw glow effect based on energy
    const energy = fish.energy !== undefined ? fish.energy : 100;
    if (energy > 70) {
      this.drawGlow(x + scaledWidth / 2, y + scaledHeight / 2, scaledWidth * 0.7, energy);
    }

    ctx.save();

    // Apply color tint if genome data available
    if (genome_data?.color_hue !== undefined) {
      // Draw image with color tinting
      this.drawImageWithColorTint(
        image,
        x,
        y,
        scaledWidth,
        scaledHeight,
        flipHorizontal,
        genome_data.color_hue
      );
    } else {
      // Draw image without tinting
      this.drawImage(image, x, y, scaledWidth, scaledHeight, flipHorizontal);
    }

    ctx.restore();

    // Draw enhanced energy bar
    if (fish.energy !== undefined) {
      this.drawEnhancedEnergyBar(x, y - 12, scaledWidth, fish.energy);
    }
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

    // Make food images smaller (0.7x scale)
    const foodScale = 0.7;
    const scaledWidth = width * foodScale;
    const scaledHeight = height * foodScale;
    // Center the smaller food at original position
    const offsetX = (width - scaledWidth) / 2;
    const offsetY = (height - scaledHeight) / 2;

    // Draw subtle shadow
    this.drawShadow(x + width / 2, y + height, scaledWidth * 0.6, scaledHeight * 0.2);

    // Add subtle glow to food
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

    // Food images don't flip
    this.drawImage(image, x + offsetX, y + offsetY, scaledWidth, scaledHeight, false);
  }

  private renderPlant(plant: EntityData, elapsedTime: number) {
    const { ctx } = this;
    const { x, y, width, height, plant_type = 1 } = plant;

    // Get plant image (plant_type is 1 or 2)
    const imageName = plant_type === 1 ? 'plant1.png' : 'plant2.png';
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

    // Make plant images 50% larger (1.5x scale)
    const plantScale = 1.5;
    const scaledWidth = width * plantScale;
    const scaledHeight = height * plantScale;

    // Apply swaying effect
    const swayRange = 5; // degrees
    const swaySpeed = 0.0005;
    const swayAngle = Math.sin(elapsedTime * swaySpeed) * swayRange;

    ctx.save();
    const canvasHeight = ctx.canvas.height;
    const seabedOffset = Math.max(40, canvasHeight * 0.08);
    const restingY = canvasHeight - seabedOffset;
    // Allow slight offset so multiple plants feel organic
    const swayOffset = Math.sin((x + y) * 0.01) * 6;
    ctx.translate(x + scaledWidth / 2 + swayOffset, restingY);
    ctx.rotate((swayAngle * Math.PI) / 180);
    ctx.drawImage(image, -scaledWidth / 2, -scaledHeight, scaledWidth, scaledHeight);
    ctx.restore();
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

  private renderCastle(castle: EntityData, _elapsedTime: number) {
    const { x, y, width, height } = castle;

    const imageName = 'castle.png';
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
    // Convert HSL color to RGB (matching pygame's color tint)
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
