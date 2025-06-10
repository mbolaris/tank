import pygame

class ImageLoader:
    """Class responsible for loading and caching images."""
    cache = {}

    @staticmethod
    def load_image(filename):
        """Load an image from a file."""
        if filename in ImageLoader.cache:
            return ImageLoader.cache[filename]
        else:
            try:
                image = pygame.image.load(filename).convert_alpha()
                ImageLoader.cache[filename] = image
                return image
            except pygame.error as e:
                raise SystemExit(f"Couldn't load image: {filename}") from e
