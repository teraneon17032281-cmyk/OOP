import math
import os
import random
import sys
from array import array

import pygame

WIDTH = 800
HEIGHT = 600

ROAD_TOP = 158
ROAD_BOTTOM = 442
ROAD_MID = 300

# Камера: игрок движется по экрану только в этих пределах по X,
# дальше он "едет" вперёд/назад, а дорога и машины прокручиваются
CAM_LEFT = 200
CAM_RIGHT = 500

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Звук мотора: "supra" (рядная шестёрка с турбиной) или "v12"
ENGINE_PROFILE = "supra"


def load_image(name):
    return pygame.image.load(os.path.join(BASE_DIR, name)).convert_alpha()


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


# ---------------------------------------------------------------- ЗВУК
TWO_PI = 2 * math.pi

# Профили мотора. Меняется одной строкой ENGINE_PROFILE вверху файла.
PROFILES = {
    # Toyota Supra 2JZ-GTE: рядная шестёрка + турбина (свист, "су-ту-ту-ту")
    "supra": dict(
        cyl=[1.0, 0.85, 0.95, 0.80, 1.0, 0.90],  # 3 выхлопа за оборот
        res=[(90, 1.0, 50), (180, 0.9, 80), (360, 0.6, 130), (700, 0.35, 200), (1300, 0.15, 300)],
        rumble_div=3,
        cruise=(168, 0.30),  # (частота выстрелов Гц, "глушитель")
        boost=(288, 0.42),
        boost_whistle=3200,
        rev=(110, 290, 0.42),
        turbo=True,
    ),
    # V12: 6 выхлопов за оборот, ровный высокий вой
    "v12": dict(
        cyl=[1.0, 0.92, 0.97, 0.90, 1.0, 0.94, 0.96, 0.90, 1.0, 0.93, 0.98, 0.91],
        res=[(180, 1.0, 80), (360, 0.8, 120), (720, 0.6, 180), (1400, 0.4, 250), (2600, 0.25, 350)],
        rumble_div=6,
        cruise=(360, 0.60),
        boost=(720, 0.75),
        boost_whistle=0,
        rev=(250, 720, 0.75),
        turbo=False,
    ),
}


class Audio:
    """Звуки: сначала ищем свои файлы в папке sounds/, иначе синтезируем в коде.

    Свои файлы (любой из форматов .wav / .ogg / .mp3):
        sounds/engine.wav   - зацикленный звук мотора на ходу
        sounds/boost.wav    - зацикленный звук мотора на высоких оборотах (Shift)
        sounds/rev.wav      - набор оборотов при нажатии Shift ("Су-у")
        sounds/flutter.wav  - сброс при отпускании Shift ("ту-ту-ту-ту")
        sounds/crash.wav    - удар
    """

    def __init__(self):
        self.enabled = False
        init = pygame.mixer.get_init()
        if init is None:
            return
        self.sr, _, self.channels = init
        self.p = PROFILES[ENGINE_PROFILE]

        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(2)
        self.ch_cruise = pygame.mixer.Channel(0)
        self.ch_boost = pygame.mixer.Channel(1)

        p = self.p
        self.cruise = self._get("engine", lambda: self._engine_loop(*p["cruise"], 0.0))
        self.boost = self._get("boost", lambda: self._engine_loop(*p["boost"], p["boost_whistle"]))
        self.rev = self._get("rev", self._make_rev)
        self.flutter = self._get("flutter", self._make_flutter if p["turbo"] else self._make_pops)
        self.crash = self._get("crash", self._make_crash)

        self.vol_cruise = 0.0
        self.vol_boost = 0.0
        self.ch_cruise.play(self.cruise, loops=-1)
        self.ch_boost.play(self.boost, loops=-1)
        self.ch_cruise.set_volume(0.0)
        self.ch_boost.set_volume(0.0)
        self.enabled = True

    def _get(self, name, maker):
        for ext in (".wav", ".ogg", ".mp3"):
            path = os.path.join(BASE_DIR, "sounds", name + ext)
            if os.path.exists(path):
                try:
                    return pygame.mixer.Sound(path)
                except pygame.error:
                    pass
        return maker()

    def _to_sound(self, samples):
        data = array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32767)
            for _ in range(self.channels):
                data.append(v)
        return pygame.mixer.Sound(buffer=data.tobytes())

    # ---- мотор: серия выхлопных импульсов -> глушитель (фильтр) -> низкий гул
    def _engine_samples(self, n, freq_at, lp_a, whistle=0.0, whistle_at=None):
        sr = self.sr
        cyl = self.p["cyl"]
        res = self.p["res"]
        div = self.p["rumble_div"]
        phase = 0.0
        rphase = 0.0
        k = 0
        y = 0.0
        x_prev = 0.0
        out_prev = 0.0
        wph = 0.0
        out = []
        for i in range(n):
            f = freq_at(i)  # частота выстрелов цилиндров, Гц
            phase += f / sr
            if phase >= 1.0:
                phase -= 1.0
                k += 1
            tau = phase / f
            s = 0.0
            for fj, aj, dj in res:
                s += aj * math.sin(TWO_PI * fj * tau) * math.exp(-dj * tau)
            s *= cyl[k % len(cyl)]

            rphase += TWO_PI * (f / div) / sr  # частота вращения коленвала
            s += 0.35 * math.sin(rphase)
            s += 0.05 * random.uniform(-1, 1)

            y += lp_a * (s - y)  # "глушитель": срезаем визг
            o = y - x_prev + 0.995 * out_prev  # убираем постоянную составляющую
            x_prev = y
            out_prev = o
            o = math.tanh(1.6 * o)  # лёгкая перегрузка = хрипотца

            if whistle_at is not None:
                wf, wa = whistle_at(i)
                wph += TWO_PI * wf / sr
                o += wa * math.sin(wph)
            elif whistle:
                o += 0.05 * math.sin(TWO_PI * whistle * i / sr)
            out.append(o)
        return out

    @staticmethod
    def _normalize(samples, peak=0.8):
        m = max(abs(s) for s in samples) or 1.0
        return [s * peak / m for s in samples]

    def _engine_loop(self, firing_hz, lp_a, whistle):
        n = int(self.sr * 0.5)
        # считаем 2 круга и берём второй: фильтры успевают "прогреться",
        # петля получается без щелчка
        raw = self._engine_samples(2 * n, lambda i: firing_hz, lp_a, whistle=whistle)
        return self._to_sound(self._normalize(raw[n:], 0.75))

    def _make_rev(self):
        # "Су-у-у": обороты растут, нарастает свист турбины и шум впуска
        sr = self.sr
        n = int(sr * 1.0)
        f0, f1, lp_a = self.p["rev"]
        turbo = self.p["turbo"]

        def freq_at(i):
            p = i / n
            return f0 + (f1 - f0) * (1 - (1 - p) ** 2)

        def whistle_at(i):
            p = i / n
            wf = 1400 + 2800 * p * p
            wa = 0.30 * min(1.0, p * 3) * min(1.0, (1 - p) / 0.25)
            return wf, wa

        raw = self._engine_samples(n, freq_at, lp_a, whistle_at=whistle_at if turbo else None)
        out = self._normalize(raw, 0.8)

        lp1 = lp2 = 0.0
        fade = int(sr * 0.25)
        for i in range(n):
            p = i / n
            x = random.uniform(-1, 1)
            lp1 += 0.3 * (x - lp1)
            lp2 += 0.05 * (lp1 - lp2)
            if turbo:
                out[i] += 0.9 * (lp1 - lp2) * p * p  # "ш-ш-ш" всасываемого воздуха
            env = min(1.0, i / (sr * 0.01)) * min(1.0, (n - i) / fade)
            out[i] = math.tanh(out[i]) * env
        return self._to_sound(out)

    def _make_flutter(self):
        # "Ту-ту-ту-ту": срыв потока на турбине. Каждый "ту" - короткий
        # всплеск шума с падающим по высоте свистом, частота всплесков
        # постепенно замедляется; под ним затухает вой турбины и шипит сброс.
        sr = self.sr
        n = int(sr * 1.4)
        bursts = []
        t, rate, amp = 0.03, 15.0, 1.0
        for _ in range(11):
            bursts.append((t, amp * random.uniform(0.85, 1.0)))
            t += 1.0 / rate
            rate *= 0.93
            amp *= 0.90

        lp_a = 0.0
        lp_b = 0.0
        wph = 0.0
        out = []
        for i in range(n):
            ti = i / sr
            x = random.uniform(-1, 1)
            lp_a += 0.5 * (x - lp_a)
            lp_b += 0.08 * (lp_a - lp_b)
            band = lp_a - lp_b  # шум примерно 250 Гц - 3.5 кГц
            hiss = x - lp_a  # только верха

            s = 0.0
            for t0, a in bursts:
                d = ti - t0
                if 0 <= d < 0.06:
                    env = min(1.0, d * 600) * math.exp(-d * 70)
                    ph = TWO_PI * (900 * d + 1700 * (1 - math.exp(-40 * d)) / 40)
                    body = math.sin(TWO_PI * 180 * d)
                    s += a * env * (0.55 * math.sin(ph) + 1.1 * band + 0.3 * body)

            if ti < 0.9:  # затухающий вой турбины
                q = ti / 0.9
                wph += TWO_PI * (3200 - 1900 * q) / sr
                s += 0.12 * math.sin(wph) * (1 - q) ** 1.5

            s += 0.35 * hiss * math.exp(-ti * 4) * min(1.0, ti * 30)  # "пшш"
            out.append(s)
        out = self._normalize(out, 1.0)
        return self._to_sound([math.tanh(1.4 * v) * 0.9 for v in out])

    def _make_pops(self):
        # сброс газа V12: серия хлопков из выхлопа
        sr = self.sr
        n = int(sr * 1.0)
        pops = []
        t, amp = 0.02, 1.0
        for _ in range(14):
            pops.append((t, amp * random.uniform(0.6, 1.0)))
            t += random.uniform(0.03, 0.09)
            amp *= 0.93

        lp = 0.0
        out = []
        for i in range(n):
            ti = i / sr
            x = random.uniform(-1, 1)
            lp += 0.35 * (x - lp)
            s = 0.0
            for t0, a in pops:
                d = ti - t0
                if 0 <= d < 0.15:
                    ph = TWO_PI * (45 * d + 60 * (1 - math.exp(-35 * d)) / 35)
                    thump = math.sin(ph) * math.exp(-d * 35)
                    crack = (x - lp) * math.exp(-d * 120) * 1.4
                    s += a * (thump + crack)
            out.append(s)
        out = self._normalize(out, 1.0)
        return self._to_sound([math.tanh(1.5 * v) * 0.9 for v in out])

    def _make_crash(self):
        n = int(self.sr * 0.9)
        phase = 0.0
        lp = 0.0
        out = []
        for i in range(n):
            t = i / self.sr
            # низкий удар кузова
            f = 50 + 60 * math.exp(-10 * t)
            phase += TWO_PI * f / self.sr
            thump = math.sin(phase) * math.exp(-6 * t)
            # хруст металла
            x = random.uniform(-1, 1)
            lp += 0.4 * (x - lp)
            crunch = (0.6 * x + 0.4 * lp) * math.exp(-7 * t) * 0.9
            # звон металла
            metal = 0.0
            for fm in (420, 690, 1130, 1710):
                metal += math.sin(TWO_PI * fm * t)
            metal *= 0.10 * math.exp(-16 * t)
            # осколки
            debris = 0.0
            for t0, a in ((0.07, 0.30), (0.16, 0.20), (0.27, 0.12)):
                if t > t0:
                    debris += random.uniform(-1, 1) * a * math.exp(-(t - t0) * 30)
            out.append(thump + crunch + metal + debris)
        peak = max(abs(s) for s in out) or 1.0
        out = [math.tanh(1.3 * s / peak) * 0.95 for s in out]
        return self._to_sound(out)

    def update(self, boosting, moving):
        if not self.enabled:
            return
        target_cruise = 0.0 if boosting else (0.6 if moving else 0.45)
        target_boost = 0.75 if boosting else 0.0
        self.vol_cruise += (target_cruise - self.vol_cruise) * 0.12
        self.vol_boost += (target_boost - self.vol_boost) * 0.12
        self.ch_cruise.set_volume(self.vol_cruise)
        self.ch_boost.set_volume(self.vol_boost)

    def play_rev(self):
        if self.enabled:
            self.rev.set_volume(0.85)
            self.rev.play()

    def play_release(self):
        if self.enabled:
            self.flutter.set_volume(0.9)
            self.flutter.play()

    def play_crash(self, strength):
        if self.enabled:
            self.crash.set_volume(0.4 + 0.6 * strength)
            self.crash.play()


# ---------------------------------------------------------------- ИГРОК
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames_right = [
            load_image("car1.png"),
            load_image("car2.png"),
            load_image("car3.png"),
            load_image("car4.png"),
        ]
        self.frames_left = []
        for img in self.frames_right:
            self.frames_left.append(pygame.transform.flip(img, True, False))

        self.direction = "right"
        self.frame_index = 0
        self.image = self.frames_right[0]

        self.rect = self.image.get_rect(center=(x, y))

        self.base_speed = 5
        self.boost_speed = 7
        self.speed = self.base_speed
        self.is_boosting = False
        self.moving = False
        self.anim_timer = 0

        # скорость за кадр (нужна для расчёта силы удара)
        self.vx = 0
        self.vy = 0
        # отброс после столкновения
        self.knock_x = 0.0
        self.knock_y = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.hit_cooldown = 0

    def update(self):
        keys = pygame.key.get_pressed()
        vx = 0
        vy = 0

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            self.is_boosting = True
            self.speed = self.boost_speed
        else:
            self.is_boosting = False
            self.speed = self.base_speed

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx -= self.speed
            self.direction = "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx += self.speed
            self.direction = "right"
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            vy -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            vy += self.speed

        self.vx = vx
        self.vy = vy
        self.moving = vx != 0 or vy != 0
        self.rect.x += vx
        self.rect.y += vy

        # отброс после удара (затухает)
        self.acc_x += self.knock_x
        self.acc_y += self.knock_y
        step_x = int(self.acc_x)
        step_y = int(self.acc_y)
        self.rect.x += step_x
        self.rect.y += step_y
        self.acc_x -= step_x
        self.acc_y -= step_y
        self.knock_x *= 0.86
        self.knock_y *= 0.86
        if abs(self.knock_x) < 0.2:
            self.knock_x = 0.0
        if abs(self.knock_y) < 0.2:
            self.knock_y = 0.0

        self.check_bounds()

        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1

        self.anim_timer += 1
        if self.is_boosting:
            delay = 3
        elif self.moving:
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


# ---------------------------------------------------------------- ТРАФИК
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
        self.pos_x = 0.0
        self.slow = 1.0

        self.spawn(start=True)

    def get_y_limits(self):
        half = self.rect.height // 2
        if self.oncoming:
            return ROAD_TOP + 8 + half, ROAD_MID - 8 - half
        else:
            return ROAD_MID + 8 + half, ROAD_BOTTOM - 8 - half

    def spawn(self, start=False, side=None):
        y1, y2 = self.get_y_limits()
        y = random.randint(y1, y2)

        if side is None:
            side = "right" if self.oncoming else "left"

        if start:
            x = random.randint(0, WIDTH)
        elif side == "right":
            x = WIDTH + random.randint(60, 450)
        else:
            x = -random.randint(60, 450)

        self.pos_x = float(x)
        self.rect.center = (x, y)
        self.target_y = y
        self.slow = 1.0

        if self.oncoming:
            self.speed = random.uniform(3, 7)
        else:
            self.speed = random.uniform(1.5, 4)

        self.lane_timer = random.randint(60, 240)

    def vel_x(self):
        v = self.speed * self.slow
        return -v if self.oncoming else v

    def shift(self, dx, dy):
        self.pos_x += dx
        self.rect.centerx = round(self.pos_x)
        self.rect.centery += dy

    def nudge_lane(self, dy):
        y1, y2 = self.get_y_limits()
        self.target_y = max(y1, min(y2, self.target_y + dy))
        self.lane_timer = 120

    def update(self):
        self.pos_x += self.vel_x()
        self.rect.centerx = round(self.pos_x)

        # после удара машина постепенно набирает скорость обратно
        self.slow += (1.0 - self.slow) * 0.02

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

        # машины, оставшиеся далеко позади, возвращаются впереди
        if self.oncoming:
            if self.rect.right < -20 or self.rect.left > WIDTH + 600:
                self.spawn(side="right")
        else:
            if self.rect.left > WIDTH + 20:
                self.spawn(side="left")
            elif self.rect.right < -600:
                self.spawn(side="right")


# ---------------------------------------------------------------- ИГРА
class Game:
    def __init__(self):
        # моно 16 бит - так проще генерировать звуки
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.world = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("PYGAME GAME")

        self.clock = pygame.time.Clock()
        self.fps = 60
        self.is_running = True
        self.font = pygame.font.SysFont("arial", 22, bold=True)

        try:
            self.audio = Audio()
        except Exception as e:  # нет звуковой карты и т.п. - играем без звука
            print("Звук недоступен:", e)
            self.audio = Audio.__new__(Audio)
            self.audio.enabled = False

        self.player = Player(WIDTH // 2, HEIGHT // 2)
        self.all_sprites = pygame.sprite.Group(self.player)

        self.traffic = pygame.sprite.Group()
        colors = [(0, 2, 1), (1, 0, 2), (2, 1, 0), (1, 2, 0), (2, 0, 1)]

        for i in range(6):
            car = Traffic(self.player.frames_right, colors, oncoming=(i % 2 == 0))
            self.traffic.add(car)

        self.hits = 0
        self.road_offset = 0
        self.was_boosting = False
        self.shake_time = 0
        self.shake_power = 0.0

    def run(self):
        while self.is_running:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)

        pygame.mixer.stop()
        pygame.quit()
        sys.exit()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False

    def handle_collisions(self):
        p = self.player
        for car in self.traffic:
            if not pygame.sprite.collide_mask(p, car):
                continue

            # в какую сторону оттолкнуть игрока: по горизонтали или вертикали
            dx = p.rect.centerx - car.rect.centerx
            dy = p.rect.centery - car.rect.centery
            nx = dx / ((p.rect.width + car.rect.width) / 2)
            ny = dy / ((p.rect.height + car.rect.height) / 2)
            if abs(nx) >= abs(ny):
                sx, sy = (1 if dx >= 0 else -1), 0
            else:
                sx, sy = 0, (1 if dy >= 0 else -1)

            # скорость сближения вдоль направления удара
            if sx:
                p_vn = (p.vx + p.knock_x) * sx
                car_vn = car.vel_x() * sx
            else:
                p_vn = (p.vy + p.knock_y) * sy
                car_vn = 0.0
            impact = max(0.0, car_vn - p_vn)

            # физически разводим машины - сквозь друг друга ехать нельзя
            for i in range(60):
                if not pygame.sprite.collide_mask(p, car):
                    break
                if i < 25:
                    p.rect.x += sx * 2
                    p.rect.y += sy * 2
                    p.check_bounds()
                else:
                    # игрок упёрся в край - сдвигаем чужую машину
                    car.shift(-sx * 2, -sy * 2)

            # сам удар: звук, тряска, отброс, замедление чужой машины
            if impact > 1.5 and p.hit_cooldown == 0:
                self.hits += 1
                p.hit_cooldown = 40
                strength = min(1.0, impact / 12)

                p.knock_x += sx * min(impact * 0.7, 9)
                p.knock_y += sy * min(impact * 0.7, 6)

                car.slow = 0.25
                if sy:
                    car.nudge_lane(-sy * 40)

                self.audio.play_crash(strength)
                self.shake_time = 18
                self.shake_power = 3 + 7 * strength

    def scroll_camera(self):
        # дорога бесконечная: у границы экрана камера едет за игроком
        p = self.player
        if p.rect.centerx > CAM_RIGHT:
            dx = p.rect.centerx - CAM_RIGHT
        elif p.rect.centerx < CAM_LEFT:
            dx = p.rect.centerx - CAM_LEFT
        else:
            return
        p.rect.centerx -= dx
        for car in self.traffic:
            car.pos_x -= dx
            car.rect.centerx = round(car.pos_x)
        self.road_offset -= dx

    def update(self):
        self.player.update()
        self.traffic.update()
        self.handle_collisions()
        self.scroll_camera()

        # звук ускорения: газ при нажатии Shift и сброс при отпускании
        boosting = self.player.is_boosting
        if boosting and not self.was_boosting:
            self.audio.play_rev()
        elif not boosting and self.was_boosting:
            self.audio.play_release()
        self.was_boosting = boosting
        self.audio.update(boosting, self.player.moving)

        if self.shake_time > 0:
            self.shake_time -= 1

        if boosting:
            self.road_offset -= 9
        else:
            self.road_offset -= 6

        self.road_offset %= 100

    def draw(self):
        surf = self.world
        surf.fill((75, 140, 65))
        pygame.draw.rect(surf, (60, 64, 72), (0, 150, WIDTH, 300))

        pygame.draw.rect(surf, (220, 220, 220), (0, 150, WIDTH, 8))
        pygame.draw.rect(surf, (220, 220, 220), (0, 442, WIDTH, 8))

        for i in range(-1, 11):
            x = i * 100 + self.road_offset
            pygame.draw.rect(surf, (240, 200, 60), (x, ROAD_MID - 5, 50, 10))

        self.traffic.draw(surf)
        self.all_sprites.draw(surf)

        # тряска экрана при ударе
        ox = oy = 0
        if self.shake_time > 0:
            power = int(self.shake_power * self.shake_time / 18) + 1
            ox = random.randint(-power, power)
            oy = random.randint(-power, power)
        self.screen.fill((75, 140, 65))
        self.screen.blit(surf, (ox, oy))

        info = f"Столкновения: {self.hits}   |   Shift - ускорение   |   Esc - выход"
        self.screen.blit(self.font.render(info, True, (255, 255, 255)), (15, 15))

        if self.player.is_boosting:
            self.screen.blit(self.font.render("TURBO!", True, (255, 210, 60)), (15, 50))

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
