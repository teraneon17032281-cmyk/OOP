import pygame
import sys

class Game:
    def __init__(self):
        pygame.init()
        self.screen_widht = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_widht, self.screen_height))
        pygame.display.set_caption("PYGAME GAME")

        self.clock = pygame.time.Clock()
        self.fps = 60

        self.is_running = True

    def run(self):
        while self.is_running:
            self._check_events()
            self._update()
            self._draw()

            self.clock.tick(self.fps)
        pygame.quit()
        sys.exit()

    def _check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False

    def _update(self):
        pass

    def _draw(self):
        self.screen.fill((40, 44, 52))

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
