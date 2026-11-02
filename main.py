import pygame
import sys

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # кадры для анимации машинки
        self.frames_right = [
            pygame.image.load("car1.png").convert_alpha(),
            pygame.image.load("car2.png").convert_alpha(),
            pygame.image.load("car3.png").convert_alpha(),
            pygame.image.load("car4.png").convert_alpha()
        ]
        # отражаем картинки для езды влево
        self.frames_left = [
            pygame.transform.flip(img, True, False) for img in self.frames_right
        ]

        self.direction = "right"
        self.frame_index = 0
        self.image = self.frames_right[self.frame_index]

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

        self.speed = 5
        self.anim_timer = 0

    def update(self):
        keys = pygame.key.get_pressed()
        is_moving = False

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
            self.direction = "left"
            is_moving = True

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
            self.direction = "right"
            is_moving = True

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rect.y -= self.speed
            is_moving = True

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.rect.y += self.speed
            is_moving = True

        # чтобы машинка не уезжала за края окна и держалась дороги
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > 800:
            self.rect.right = 800
        if self.rect.top < 140:
            self.rect.top = 140
        if self.rect.bottom > 460:
            self.rect.bottom = 460

        # анимация колес и дыма
        self.anim_timer += 1
        # если жмем кнопки - анимация быстрее, если стоим - медленнее
        delay = 5 if is_moving else 12
        if self.anim_timer >= delay:
            self.anim_timer = 0
            self.frame_index += 1
            if self.frame_index >= 4:
                self.frame_index = 0

            if self.direction == "right":
                self.image = self.frames_right[self.frame_index]
            else:
                self.image = self.frames_left[self.frame_index]


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

        self.player = Player(self.screen_widht // 2, self.screen_height // 2)

        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.player)

        # смещение полосок на дороге для эффекта движения
        self.road_offset = 0

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
        self.all_sprites.update()

        # двигаем разметку дороги чтобы казалось что мы едем по трассе
        self.road_offset -= 6
        if self.road_offset <= -100:
            self.road_offset = 0

    def _draw(self):
        # зеленая трава сверху и снизу
        self.screen.fill((75, 140, 65))

        # серая дорога по центру
        pygame.draw.rect(self.screen, (60, 64, 72), (0, 150, self.screen_widht, 300))

        # белые бордюры по краям дороги
        pygame.draw.rect(self.screen, (220, 220, 220), (0, 150, self.screen_widht, 8))
        pygame.draw.rect(self.screen, (220, 220, 220), (0, 442, self.screen_widht, 8))

        # белые бегущие полоски разметки
        for i in range(10):
            line_x = i * 100 + self.road_offset
            pygame.draw.rect(self.screen, (240, 240, 240), (line_x, 295, 50, 10))

        self.all_sprites.draw(self.screen)

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
