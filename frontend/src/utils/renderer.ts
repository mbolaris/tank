/**
 * Canvas rendering utilities for the simulation
 */

import type { EntityData } from '../types/simulation';

export class Renderer {
  private ctx: CanvasRenderingContext2D;

  constructor(ctx: CanvasRenderingContext2D) {
    this.ctx = ctx;
  }

  clear(width: number, height: number) {
    // Clear with ocean blue background
    this.ctx.fillStyle = '#1a4d6d';
    this.ctx.fillRect(0, 0, width, height);
  }

  renderEntity(entity: EntityData) {
    switch (entity.type) {
      case 'fish':
        this.renderFish(entity);
        break;
      case 'food':
        this.renderFood(entity);
        break;
      case 'plant':
        this.renderPlant(entity);
        break;
      case 'crab':
        this.renderCrab(entity);
        break;
      case 'castle':
        this.renderCastle(entity);
        break;
    }
  }

  private renderFish(fish: EntityData) {
    const { ctx } = this;
    const { x, y, width, height, energy = 100, species = 'solo', genome_data } = fish;

    // Get color based on species
    let color = '#ff6b6b';
    if (species === 'neural') {
      color = '#4ecdc4';
    } else if (species === 'algorithmic') {
      color = '#ffe66d';
    } else if (species === 'schooling') {
      color = '#a8dadc';
    }

    // Apply genome color hue if available
    if (genome_data?.color_hue !== undefined) {
      color = `hsl(${genome_data.color_hue}, 70%, 60%)`;
    }

    // Draw fish body (simple oval)
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.ellipse(x + width / 2, y + height / 2, width / 2, height / 3, 0, 0, 2 * Math.PI);
    ctx.fill();

    // Draw tail (triangle)
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, y + height / 2);
    ctx.lineTo(x - width / 4, y + height / 4);
    ctx.lineTo(x - width / 4, y + (3 * height) / 4);
    ctx.closePath();
    ctx.fill();

    // Draw eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(x + (2 * width) / 3, y + height / 3, 3, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.arc(x + (2 * width) / 3, y + height / 3, 1.5, 0, 2 * Math.PI);
    ctx.fill();

    // Draw energy bar
    this.drawEnergyBar(x, y - 10, width, energy);
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

  private renderFood(food: EntityData) {
    const { ctx } = this;
    const { x, y, width, height } = food;

    // Draw food as a circle
    ctx.fillStyle = '#8b4513';
    ctx.beginPath();
    ctx.arc(x + width / 2, y + height / 2, Math.min(width, height) / 2, 0, 2 * Math.PI);
    ctx.fill();

    // Add highlight
    ctx.fillStyle = '#a0522d';
    ctx.beginPath();
    ctx.arc(x + width / 2 - 2, y + height / 2 - 2, Math.min(width, height) / 4, 0, 2 * Math.PI);
    ctx.fill();
  }

  private renderPlant(plant: EntityData) {
    const { ctx } = this;
    const { x, y, width, height } = plant;

    // Draw plant as a simple seaweed
    ctx.strokeStyle = '#2d6a4f';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x + width / 2, y + height);

    // Wavy stem
    for (let i = 0; i <= 10; i++) {
      const yPos = y + height - (i * height) / 10;
      const xOffset = Math.sin(i * 0.5) * 5;
      ctx.lineTo(x + width / 2 + xOffset, yPos);
    }
    ctx.stroke();

    // Leaves
    ctx.fillStyle = '#40916c';
    for (let i = 2; i <= 8; i += 2) {
      const yPos = y + height - (i * height) / 10;
      const xOffset = Math.sin(i * 0.5) * 5;

      // Left leaf
      ctx.beginPath();
      ctx.ellipse(x + width / 2 + xOffset - 8, yPos, 6, 10, -Math.PI / 4, 0, 2 * Math.PI);
      ctx.fill();

      // Right leaf
      ctx.beginPath();
      ctx.ellipse(x + width / 2 + xOffset + 8, yPos, 6, 10, Math.PI / 4, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  private renderCrab(crab: EntityData) {
    const { ctx } = this;
    const { x, y, width, height } = crab;

    // Draw crab body
    ctx.fillStyle = '#ff6b35';
    ctx.beginPath();
    ctx.ellipse(x + width / 2, y + height / 2, width / 2, height / 3, 0, 0, 2 * Math.PI);
    ctx.fill();

    // Draw claws
    ctx.fillStyle = '#ff8c61';
    // Left claw
    ctx.beginPath();
    ctx.arc(x + width / 4, y + height / 2, 6, 0, 2 * Math.PI);
    ctx.fill();
    // Right claw
    ctx.beginPath();
    ctx.arc(x + (3 * width) / 4, y + height / 2, 6, 0, 2 * Math.PI);
    ctx.fill();

    // Draw eyes
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.arc(x + width / 3, y + height / 3, 2, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x + (2 * width) / 3, y + height / 3, 2, 0, 2 * Math.PI);
    ctx.fill();
  }

  private renderCastle(castle: EntityData) {
    const { ctx } = this;
    const { x, y, width, height } = castle;

    // Draw castle as a simple structure
    ctx.fillStyle = '#6c757d';

    // Main body
    ctx.fillRect(x, y + height / 3, width, (2 * height) / 3);

    // Towers
    ctx.fillRect(x, y, width / 4, height);
    ctx.fillRect(x + (3 * width) / 4, y, width / 4, height);

    // Tower tops
    ctx.fillStyle = '#495057';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + width / 8, y - height / 6);
    ctx.lineTo(x + width / 4, y);
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(x + (3 * width) / 4, y);
    ctx.lineTo(x + (7 * width) / 8, y - height / 6);
    ctx.lineTo(x + width, y);
    ctx.fill();

    // Door
    ctx.fillStyle = '#212529';
    ctx.fillRect(x + width / 3, y + (2 * height) / 3, width / 3, height / 3);
  }
}
