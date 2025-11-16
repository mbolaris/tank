/**
 * Canvas rendering utilities for the simulation using actual game images
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

export class Renderer {
  private ctx: CanvasRenderingContext2D;

  constructor(ctx: CanvasRenderingContext2D) {
    this.ctx = ctx;
  }

  clear(width: number, height: number) {
    // Create subtle ocean gradient
    const gradient = this.ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, '#04233d');
    gradient.addColorStop(0.45, '#0b4161');
    gradient.addColorStop(1, '#0f202c');
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(0, 0, width, height);

    // Soft light rays for depth
    this.ctx.save();
    this.ctx.globalAlpha = 0.12;
    for (let i = 0; i < 3; i += 1) {
      this.ctx.beginPath();
      this.ctx.moveTo((width / 3) * i + 80, 0);
      this.ctx.lineTo((width / 3) * i + 200, 0);
      this.ctx.lineTo((width / 3) * i, height);
      this.ctx.closePath();
      this.ctx.fillStyle = '#3dd5ff';
      this.ctx.fill();
    }
    this.ctx.restore();

    // Draw seabed so plants have a home
    const seabedHeight = Math.max(50, height * 0.12);
    const seabedGradient = this.ctx.createLinearGradient(
      0,
      height - seabedHeight,
      0,
      height
    );
    seabedGradient.addColorStop(0, 'rgba(227, 188, 117, 0.2)');
    seabedGradient.addColorStop(1, 'rgba(195, 161, 90, 0.35)');
    this.ctx.fillStyle = seabedGradient;
    this.ctx.fillRect(0, height - seabedHeight, width, seabedHeight);
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

    // Draw energy bar
    if (fish.energy !== undefined) {
      this.drawEnergyBar(x, y - 10, scaledWidth, fish.energy);
    }
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

    // Food images don't flip
    this.drawImage(image, x, y, width, height, false);
  }

  private renderPlant(plant: EntityData, elapsedTime: number) {
    const { ctx } = this;
    const { x, y, width, height, plant_type = 1 } = plant;

    // Get plant image (plant_type is 1 or 2)
    const imageName = plant_type === 1 ? 'plant1.png' : 'plant2.png';
    const image = ImageLoader.getCachedImage(imageName);

    if (!image) return;

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
    ctx.translate(x + width / 2 + swayOffset, restingY);
    ctx.rotate((swayAngle * Math.PI) / 180);
    ctx.drawImage(image, -width / 2, -height, width, height);
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

  private drawEnergyBar(x: number, y: number, width: number, energy: number) {
    const { ctx } = this;
    const barHeight = 4;
    const barWidth = width;

    // Background
    ctx.fillStyle = '#333333';
    ctx.fillRect(x, y, barWidth, barHeight);

    // Energy bar
    let color = '#4ade80'; // green
    if (energy < 30) {
      color = '#ef4444'; // red
    } else if (energy < 60) {
      color = '#fbbf24'; // yellow
    }

    ctx.fillStyle = color;
    ctx.fillRect(x, y, (barWidth * energy) / 100, barHeight);
  }

  private getAnimationFrame(elapsedTime: number, frameCount: number): number {
    if (frameCount <= 1) return 0;
    return Math.floor(elapsedTime / IMAGE_CHANGE_RATE) % frameCount;
  }
}
