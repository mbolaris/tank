/**
 * Image loader utility for caching and loading game images
 */

export class ImageLoader {
  private static cache: Map<string, HTMLImageElement> = new Map();
  private static loadingPromises: Map<string, Promise<HTMLImageElement>> = new Map();

  /**
   * Load an image from the public directory
   * @param filename - The filename of the image (e.g., 'george1.png')
   * @returns Promise that resolves to the loaded image
   */
  static async loadImage(filename: string): Promise<HTMLImageElement> {
    // Check cache first
    if (this.cache.has(filename)) {
      return this.cache.get(filename)!;
    }

    // Check if already loading
    if (this.loadingPromises.has(filename)) {
      return this.loadingPromises.get(filename)!;
    }

    // Load the image
    const loadPromise = new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        this.cache.set(filename, img);
        this.loadingPromises.delete(filename);
        resolve(img);
      };
      img.onerror = () => {
        this.loadingPromises.delete(filename);
        reject(new Error(`Failed to load image: ${filename}`));
      };
      img.src = `/images/${filename}`;
    });

    this.loadingPromises.set(filename, loadPromise);
    return loadPromise;
  }

  /**
   * Load multiple images at once
   * @param filenames - Array of filenames to load
   * @returns Promise that resolves when all images are loaded
   */
  static async loadImages(filenames: string[]): Promise<HTMLImageElement[]> {
    return Promise.all(filenames.map((filename) => this.loadImage(filename)));
  }

  /**
   * Get a cached image (returns null if not loaded)
   * @param filename - The filename of the image
   * @returns The cached image or null
   */
  static getCachedImage(filename: string): HTMLImageElement | null {
    return this.cache.get(filename) || null;
  }

  /**
   * Clear the image cache
   */
  static clearCache(): void {
    this.cache.clear();
    this.loadingPromises.clear();
  }

  /**
   * Preload all game images
   */
  static async preloadGameImages(): Promise<void> {
    const imageFiles = [
      'george1.png',
      'george2.png',
      'crab1.png',
      'crab2.png',
      'school.png',
      'plant1.png',
      'plant2.png',
      'castle.png',
      'food1.png',
      'food2.png',
      'food_algae1.png',
      'food_algae2.png',
      'food_energy1.png',
      'food_energy2.png',
      'food_protein1.png',
      'food_protein2.png',
      'food_rare1.png',
      'food_rare2.png',
      'food_vitamin1.png',
      'food_vitamin2.png',
    ];

    await this.loadImages(imageFiles);
  }
}
