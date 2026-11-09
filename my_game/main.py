import pygame
import random
import sys

WIDTH = 800
HEIGHT = 600

ROAD_TOP = 158
ROAD_BOTTOM = 442
ROAD_MID = 300


def change_color(frames, order):
    res = []
    for img in frames:
        copy_img = img.copy()
        w, h = copy_img.get_size()
        for x in range(w):
            for y in range(h):
                c = copy_img.get_at((x, y))
                rgb = (c.r, c.g, c.b)
                copy_img.set_at((x, y), (rgb[order[0]], rgb[order[1]], rgb[order[2]], c.a))
        res.append(copy_img)
    return res


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames_right = [
            pygame.image.load("car1.png").convert_alpha(),
            pygame.image.load("car2.png").convert_alpha(),
            pygame.image.load("car3.png").convert_alpha(),
            pygame.image.load("car4.png").convert_alpha()
        ]
        self.frames_left = []
        for img in self.frames_right:
            self.frames_left.append(pygame.transform.flip(img, True, False))

        self.direction = "right"
        self.frame_index = 0
        self.image = self.frames_right[0]

        self.rect = self.image.get_rect(center=(x, y))

        self.base_speed = 5
        self.boost_speed = 10
        self.speed = self.base_speed
        self.is_boosting = False
        self.anim_timer = 0
        self.invulnerable = 0

    def update(self):
        keys = pygame.key.get_pressed()
        moving = False

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            self.is_boosting = True
            self.speed = self.boost_speed
        else:
            self.is_boosting = False
            self.speed = self.base_speed

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
            self.direction = "left"
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
            self.direction = "right"
            moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rect.y -= self.speed
            moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.rect.y += self.speed
            moving = True

        self.check_bounds()

        if self.invulnerable > 0:
            self.invulnerable -= 1

        self.anim_timer += 1
        if self.is_boosting:
            delay = 3
        elif moving:
            delay = 5
        else:
            delay = 12

        if self.anim_timer >= delay:
            self.anim_timer = 0
            self.frame_index = (self.frame_index + 1) % 4

        if self.direction == "right":
            self.image = self.frames_right[self.frame_index]
        else:
            self.image = self.frames_left[self.frame_index]

    def check_bounds(self):
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH
        if self.rect.top < ROAD_TOP - 18:
            self.rect.top = ROAD_TOP - 18
        if self.rect.bottom > ROAD_BOTTOM + 18:
            self.rect.bottom = ROAD_BOTTOM + 18


class Traffic(pygame.sprite.Sprite):
    def __init__(self, base_frames, colors, oncoming):
        super().__init__()
        order = random.choice(colors)

        scaled = []
        for img in base_frames:
            w = int(img.get_width() * 0.75)
            h = int(img.get_height() * 0.75)
            scaled.append(pygame.transform.smoothscale(img, (w, h)))

        right_frames = change_color(scaled, order)
        left_frames = [pygame.transform.flip(img, True, False) for img in right_frames]

        self.oncoming = oncoming
        if self.oncoming:
            self.frames = left_frames
        else:
            self.frames = right_frames

        self.frame_index = random.randint(0, 3)
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.anim_timer = 0

        self.spawn(start=True)

    def get_y_limits(self):
        half = self.rect.height // 2
        if self.oncoming:
            return ROAD_TOP + 8 + half, ROAD_MID - 8 - half
        else:
            return ROAD_MID + 8 + half, ROAD_BOTTOM - 8 - half

    def spawn(self, start=False):
        y1, y2 = self.get_y_limits()
        y = random.randint(y1, y2)

        if start:
            x = random.randint(0, WIDTH)
        elif self.oncoming:
            x = WIDTH + random.randint(60, 450)
        else:
            x = -random.randint(60, 450)

        self.rect.center = (x, y)
        self.target_y = y

        if self.oncoming:
            self.speed = random.uniform(3, 7)
        else:
            self.speed = random.uniform(1.5, 4)

        self.lane_timer = random.randint(60, 240)

    def update(self):
        if self.oncoming:
            self.rect.x -= self.speed
        else:
            self.rect.x += self.speed

        self.lane_timer -= 1
        if self.lane_timer <= 0:
            y1, y2 = self.get_y_limits()
            self.target_y = random.randint(y1, y2)
            self.lane_timer = random.randint(90, 300)

        if self.rect.centery < self.target_y:
            self.rect.centery += 1
        elif self.rect.centery > self.target_y:
            self.rect.centery -= 1

        self.anim_timer += 1
        if self.anim_timer >= 6:
            self.anim_timer = 0
            self.frame_index = (self.frame_index + 1) % 4
            self.image = self.frames[self.frame_index]

        if self.oncoming and self.rect.right < -20:
            self.spawn()
        elif not self.oncoming and self.rect.left > WIDTH + 20:
            self.spawn()


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("PYGAME GAME")

        self.clock = pygame.time.Clock()
        self.fps = 60
        self.is_running = True
        self.font = pygame.font.SysFont("arial", 22, bold=True)

        self.player = Player(WIDTH // 2, HEIGHT // 2)
        self.all_sprites = pygame.sprite.Group(self.player)

        self.traffic = pygame.sprite.Group()
        colors = [(0, 2, 1), (1, 0, 2), (2, 1, 0), (1, 2, 0), (2, 0, 1)]

        for i in range(6):
            car = Traffic(self.player.frames_right, colors, oncoming=(i % 2 == 0))
            self.traffic.add(car)

        self.hits = 0
        self.road_offset = 0

    def run(self):
        while self.is_running:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)

        pygame.quit()
        sys.exit()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False

    def update(self):
        self.player.update()
        self.traffic.update()

        if self.player.invulnerable == 0:
            for car in self.traffic:
                if pygame.sprite.collide_mask(self.player, car):
                    self.hits += 1
                    self.player.invulnerable = 60
                    if self.player.rect.centerx < car.rect.centerx:
                        self.player.rect.x -= 40
                    else:
                        self.player.rect.x += 40
                    self.player.check_bounds()
                    break

        if self.player.is_boosting:
            self.road_offset -= 12
        else:
            self.road_offset -= 6

        if self.road_offset <= -100:
            self.road_offset = 0

    def draw(self):
        self.screen.fill((75, 140, 65))
        pygame.draw.rect(self.screen, (60, 64, 72), (0, 150, WIDTH, 300))

        pygame.draw.rect(self.screen, (220, 220, 220), (0, 150, WIDTH, 8))
        pygame.draw.rect(self.screen, (220, 220, 220), (0, 442, WIDTH, 8))

        for i in range(11):
            x = i * 100 + self.road_offset
            pygame.draw.rect(self.screen, (240, 200, 60), (x, ROAD_MID - 5, 50, 10))

        self.traffic.draw(self.screen)

        if self.player.invulnerable == 0 or (self.player.invulnerable // 5) % 2 == 0:
            self.all_sprites.draw(self.screen)

        info = f"Столкновения: {self.hits}   |   Shift - ускорение   |   Esc - выход"
        self.screen.blit(self.font.render(info, True, (255, 255, 255)), (15, 15))

        if self.player.is_boosting:
            self.screen.blit(self.font.render("TURBO!", True, (255, 210, 60)), (15, 50))

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
