# Author: Atanu Sarkar
# Space Invaders (my version)
# v1.1.4
# 11-April-2020, 03:04 AM (IST)

import pygame
import random
import math
from pygame import mixer
import time
import threading
import inputHandling

# import sched

# game constants
WIDTH = 800
HEIGHT = 600
BASE_FPS = 60.0

# global variables
running = True
pause_state = 0
score = 0
highest_score = 0
life = 3000
kills = 0
difficulty = 1
level = 1
max_kills_to_difficulty_up = 5
max_difficulty_to_level_up = 5
initial_player_velocity = 6.0
initial_enemy_velocity = 0.25
weapon_shot_velocity = 5.0
single_frame_rendering_time = 0
total_time = 0
frame_count = 0
fps = 0
measured_bpm = 60        # BPM captured before each level; drives auto-fire rate
last_bullet_time = 0.0   # timestamp of the last auto-fired bullet
last_setpoint_time = 0.0  # timestamp of the last setpoint send
MAX_BULLETS = 5          # max bullets on screen at once
MAX_ARC_ENEMIES = 6      # max number of arc-flying enemies
MAX_DIVE_BOMBERS = 4     # max number of vertical enemies
max_hoogte = 900
use_measured_position = True

# game objects
player = type('Player', (), {})()
bullet = type('Bullet', (), {})()  # template / prototype
bullets = []  # active bullet pool
enemies = []
lasers = []
dive_bombers = []  # second enemy type: dives straight down

input_thread = threading.Thread(target=inputHandling.init, daemon=True)
input_thread.start()

# initialize pygame
pygame.init()

# Input key states (keyboard)
LEFT_ARROW_KEY_PRESSED = 0
RIGHT_ARROW_KEY_PRESSED = 0
UP_ARROW_KEY_PRESSED = 0
SPACE_BAR_PRESSED = 0
ENTER_KEY_PRESSED = 0
ESC_KEY_PRESSED = 0
is_fullscreen = True

# create display window
window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Space Invaders")
window_icon = pygame.image.load("res/images/alien.png")
pygame.display.set_icon(window_icon)

# game sounds
pause_sound = None
level_up_sound = None
weapon_annihilation_sound = None
game_over_sound = None

# create background
background_img = pygame.image.load("res/images/background.jpg")  # 800 x 600 px image
background_music_paths = ["res/sounds/Space_Invaders_Music.ogg",
                          "res/sounds/Space_Invaders_Music_x2.ogg",
                          "res/sounds/Space_Invaders_Music_x4.ogg",
                          "res/sounds/Space_Invaders_Music_x8.ogg",
                          "res/sounds/Space_Invaders_Music_x16.ogg",
                          "res/sounds/Space_Invaders_Music_x32.ogg"]


def toggle_fullscreen():
    global window
    global is_fullscreen

    is_fullscreen = not is_fullscreen
    flags = pygame.FULLSCREEN if is_fullscreen else 0
    window = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Space Invaders")
    pygame.display.set_icon(window_icon)


def init_background_music():
    if difficulty == 1:
        mixer.quit()
        mixer.init()
    if difficulty <= 6:
        mixer.music.load(background_music_paths[difficulty - 1])
    else:
        mixer.music.load(background_music_paths[5])
    mixer.music.play(-1)


# create player class
class Player:
    def __init__(self, img_path, width, height, x, y, dx, dy, kill_sound_path):
        self.img_path = img_path
        self.img = pygame.image.load(self.img_path)
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.setpoint = x
        self.kill_sound_path = kill_sound_path
        self.kill_sound = mixer.Sound(self.kill_sound_path)

    def draw(self):
        window.blit(self.img, (self.x, self.y))


# create enemy class
class Enemy:
    def __init__(self, img_path, width, height, x, y, dx, dy, kill_sound_path):
        self.img_path = img_path
        self.img = pygame.image.load(self.img_path)
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.kill_sound_path = kill_sound_path
        self.kill_sound = mixer.Sound(self.kill_sound_path)
        self.arc_start_x = x
        self.arc_start_y = y
        self.arc_control_x = x
        self.arc_control_y = y
        self.arc_end_x = x
        self.arc_end_y = y
        self.arc_t = 0.0
        self.arc_speed = 0.003
        self.start_new_arc()

    def draw(self):
        window.blit(self.img, (self.x, self.y))

    def start_new_arc(self):
        margin = self.width + random.randint(30, 120)
        from_left = random.random() < 0.5

        if from_left:
            self.arc_start_x = -margin
            self.arc_end_x = WIDTH + margin
        else:
            self.arc_start_x = WIDTH + margin
            self.arc_end_x = -margin

        self.arc_start_y = random.randint(int(HEIGHT * 0.1), int(HEIGHT * 0.45))
        self.arc_end_y = random.randint(int(HEIGHT * 0.1), int(HEIGHT * 0.45))
        self.arc_control_x = random.randint(int(WIDTH * 0.2), int(WIDTH * 0.8))
        self.arc_control_y = random.randint(-self.height * 2, int(HEIGHT * 0.15))

        self.arc_t = 0.0
        speed_scale = max(0.5, self.dx / initial_enemy_velocity)
        self.arc_speed = random.uniform(0.0025, 0.0045) * speed_scale
        self._apply_arc_position()

    def _apply_arc_position(self):
        u = 1.0 - self.arc_t
        self.x = (u * u * self.arc_start_x) + (2 * u * self.arc_t * self.arc_control_x) + (self.arc_t * self.arc_t * self.arc_end_x)
        self.y = (u * u * self.arc_start_y) + (2 * u * self.arc_t * self.arc_control_y) + (self.arc_t * self.arc_t * self.arc_end_y)

    def move_in_arc(self, speed_multiplier, frame_scale):
        self.arc_t += self.arc_speed * speed_multiplier * frame_scale
        if self.arc_t >= 1.0:
            self.start_new_arc()
            return
        self._apply_arc_position()


# create bullet class
class Bullet:
    def __init__(self, img_path, width, height, x, y, dx, dy, fire_sound_path):
        self.img_path = img_path
        self.img = pygame.image.load(self.img_path)
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.fired = False
        self.fire_sound_path = fire_sound_path
        self.fire_sound = mixer.Sound(self.fire_sound_path)

    def draw(self):
        if self.fired:
            window.blit(self.img, (self.x, self.y))


# create laser class
class Laser:
    def __init__(self, img_path, width, height, x, y, dx, dy, shoot_probability, relaxation_time, beam_sound_path):
        self.img_path = img_path
        self.img = pygame.image.load(self.img_path)
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.beamed = False
        self.shoot_probability = shoot_probability
        self.shoot_timer = 0.0
        self.relaxation_time = relaxation_time / BASE_FPS
        self.beam_sound_path = beam_sound_path
        self.beam_sound = mixer.Sound(self.beam_sound_path)

    def draw(self):
        if self.beamed:
            window.blit(self.img, (self.x, self.y))


# create dive bomber class — moves straight down, takes a life on contact or reaching the bottom
class DiveBomber:
    def __init__(self, img_path, width, height, x, y, dy, kill_sound_path):
        self.img_path = img_path
        self.img = pygame.image.load(self.img_path)
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.dy = dy
        self.kill_sound_path = kill_sound_path
        self.kill_sound = mixer.Sound(self.kill_sound_path)

    def draw(self):
        window.blit(self.img, (self.x, self.y))

    def respawn(self):
        self.x = random.randint(0, int(WIDTH - self.width))
        self.y = random.randint(-self.height * 3, -self.height)


def scoreboard():
    x_offset = 10
    y_offset = 10
    # set font type and size
    font = pygame.font.SysFont("calibre", 16)

    # render font and text sprites
    score_sprint = font.render("SCORE : " + str(score), True, (255, 255, 255))
    highest_score_sprint = font.render("HI-SCORE : " + str(highest_score), True, (255, 255, 255))
    level_sprint = font.render("LEVEL : " + str(level), True, (255, 255, 255))
    difficulty_sprint = font.render("DIFFICULTY : " + str(difficulty), True, (255, 255, 255))
    life_sprint = font.render("LIFE LEFT : " + str(life) + " | " + ("@ " * life), True, (255, 255, 255))
    BPM_sprint = font.render("BPM : " + f"{inputHandling.getBPM():.2f}", True, (255, 255, 255))
    BPMlevel_sprint = font.render("BPM level : " + f"{measured_bpm}", True, (255, 255, 255))

    # performance info
    fps_sprint = font.render("FPS : " + str(fps), True, (255, 255, 255))
    frame_time_in_ms = round(single_frame_rendering_time * 1000, 2)
    frame_time_sprint = font.render("FT : " + str(frame_time_in_ms) + " ms", True, (255, 255, 255))

    # place the font sprites on the screen
    window.blit(score_sprint, (x_offset, y_offset))
    window.blit(highest_score_sprint, (x_offset, y_offset + 20))
    window.blit(level_sprint, (x_offset, y_offset + 40))
    window.blit(difficulty_sprint, (x_offset, y_offset + 60))
    window.blit(life_sprint, (x_offset, y_offset + 80))
    window.blit(BPM_sprint, (x_offset, y_offset + 100))
    window.blit(BPMlevel_sprint, (x_offset, y_offset + 120))
    window.blit(fps_sprint, (WIDTH - 80, y_offset))
    window.blit(frame_time_sprint, (WIDTH - 80, y_offset + 20))


def collision_check(object1, object2):
    x1_cm = object1.x + object1.width / 2
    y1_cm = object1.y + object1.width / 2
    x2_cm = object2.x + object2.width / 2
    y2_cm = object2.y + object2.width / 2
    distance = math.sqrt(math.pow((x2_cm - x1_cm), 2) + math.pow((y2_cm - y1_cm), 2))
    return distance < ((object1.width + object2.width) / 2)


# def collision_check(object1_x, object1_y, object1_diameter, object2_x, object2_y, object2_diameter):
#     x1_cm = object1_x + object1_diameter / 2
#     y1_cm = object1_y + object1_diameter / 2
#     x2_cm = object2_x + object2_diameter / 2
#     y2_cm = object2_y + object2_diameter / 2
#     distance = math.sqrt(math.pow((x2_cm - x1_cm), 2) + math.pow((y2_cm - y1_cm), 2))
#     return distance < ((object1_diameter + object2_diameter) / 2)


def level_up():
    global life
    global level
    global difficulty
    global max_difficulty_to_level_up
    level_up_sound.play()
    level += 1
    life += 1       # grant a life
    difficulty = 1  # reset difficulty
    # TODO: change player and bullet speeds, enemy laser speed and firing probability wrt level
    #  come up with interesting gameplay ideas.
    #  variables in hand:
    #  1. speed of weapons
    #  2. enemy (up to 6) & player velocity
    #  3. laser firing probability
    #  future ideas:
    #  1. add new type of enemies
    #  2. add new player spaceship and bullets!
    #  future features:
    #  1. create player profile ad store highest score to DB
    #  2. multiplayer
    if level % 3 == 0:
        player.dx += 1
        bullet.dy += 1
        for b in bullets:
            b.dy += 1
        max_difficulty_to_level_up += 1
        for each_laser in lasers:
            each_laser.shoot_probability += 0.1
            if each_laser.shoot_probability > 1.0:
                each_laser.shoot_probability = 1.0
    if max_difficulty_to_level_up > 7:
        max_difficulty_to_level_up = 7

    font = pygame.font.SysFont("freesansbold", 64)
    gameover_sprint = font.render("LEVEL UP", True, (255, 255, 255))
    window.blit(gameover_sprint, (WIDTH / 2 - 120, HEIGHT / 2 - 32))
    pygame.display.update()
    init_game()
    time.sleep(1.0)
    measure_heartrate_screen()  # measure BPM before the new level begins


def respawn(enemy_obj):
    enemy_obj.start_new_arc()


def kill_enemy(player_obj, bullet_obj, enemy_obj):
    global score
    global kills
    global difficulty
    bullet_obj.fired = False
    enemy_obj.kill_sound.play()
    bullet_obj.x = player_obj.x + player_obj.width / 2 - bullet_obj.width / 2
    bullet_obj.y = player_obj.y + bullet_obj.height / 2
    score = score + 10 * difficulty * level
    kills += 1
    if kills % max_kills_to_difficulty_up == 0:
        difficulty += 1
        if (difficulty == max_difficulty_to_level_up) and (life != 0):
            level_up()
        init_background_music()
    print("Score:", score)
    print("level:", level)
    print("difficulty:", difficulty)
    respawn(enemy_obj)


def rebirth(player_obj):
    # keep horizontal position — only restore vertical position
    player_obj.y = (HEIGHT / 10) * 9 - (player_obj.height / 2)


def gameover_screen():
    scoreboard()
    font = pygame.font.SysFont("freesansbold", 64)
    gameover_sprint = font.render("GAME OVER", True, (255, 255, 255))
    window.blit(gameover_sprint, (WIDTH / 2 - 140, HEIGHT / 2 - 32))
    pygame.display.update()

    mixer.music.stop()
    game_over_sound.play()
    time.sleep(13.0)
    mixer.quit()


def gameover():
    global running
    global score
    global highest_score

    if score > highest_score:
        highest_score = score

    # console display
    print("----------------")
    print("GAME OVER !!")
    print("----------------")
    print("you died at")
    print("Level:", level)
    print("difficulty:", difficulty)
    print("Your Score:", score)
    print("----------------")
    print("Try Again !!")
    print("----------------")
    running = False
    gameover_screen()


def kill_player(player_obj, enemy_obj, laser_obj):
    global life
    laser_obj.beamed = False
    player_obj.kill_sound.play()
    laser_obj.x = enemy_obj.x + enemy_obj.width / 2 - laser_obj.width / 2
    laser_obj.y = enemy_obj.y + laser_obj.height / 2
    life -= 1
    print("Life Left:", life)
    if life > 0:
        rebirth(player_obj)
    else:
        gameover()


def destroy_weapons(player_obj, bullet_obj, enemy_obj, laser_obj):
    bullet_obj.fired = False
    laser_obj.beamed = False
    weapon_annihilation_sound.play()
    bullet_obj.x = player_obj.x + player_obj.width / 2 - bullet_obj.width / 2
    bullet_obj.y = player_obj.y + bullet_obj.height / 2
    laser_obj.x = enemy_obj.x + enemy_obj.width / 2 - laser_obj.width / 2
    laser_obj.y = enemy_obj.y + laser_obj.height / 2


# timer = sched.scheduler(time.time, time.sleep)
#
#
# def calculate_fps(sc):
#     global frame_count
#     fps = frame_count
#     print("FPS =", fps)
#     frame_count = 0
#     timer.enter(60, 1, calculate_fps, (sc,))
#
#
# timer.enter(60, 1, calculate_fps, (timer, ))
# timer.run()


def pause_game():
    pause_sound.play()
    scoreboard()
    font = pygame.font.SysFont("freesansbold", 64)
    gameover_sprint = font.render("PAUSED", True, (255, 255, 255))
    window.blit(gameover_sprint, (WIDTH / 2 - 80, HEIGHT / 2 - 32))
    pygame.display.update()
    mixer.music.pause()


def measure_heartrate_screen(duration=10):
    """Block until a heart-rate measurement is complete.

    Shows a live BPM readout and a countdown.  After *duration* seconds the
    last stable BPM reading is stored in the global ``measured_bpm``.  The
    game (and music) are paused for the entire measurement.
    """
    global measured_bpm

    mixer.music.pause()

    font_title = pygame.font.SysFont("freesansbold", 42)
    font_bpm   = pygame.font.SysFont("freesansbold", 64)
    font_small = pygame.font.SysFont("freesansbold", 24)

    start = time.time()

    while True:
        elapsed   = time.time() - start
        remaining = max(0.0, duration - elapsed)

        # keep the pygame event queue alive so the window stays responsive
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit

        # draw measurement screen
        window.fill((0, 0, 0))
        window.blit(background_img, (0, 0))

        title_surf = font_title.render("MEASURING HEART RATE", True, (255, 255, 0))
        window.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 2 - 100))

        live_bpm = inputHandling.getBPM()
        bpm_color = (100, 220, 100) if live_bpm > 0 else (180, 180, 180)
        bpm_surf = font_bpm.render(f"{live_bpm:.1f} BPM", True, bpm_color)
        window.blit(bpm_surf, (WIDTH // 2 - bpm_surf.get_width() // 2, HEIGHT // 2 - 30))

        hint = "Keep your finger on the sensor" if live_bpm <= 0 else "Hold still..."
        hint_surf = font_small.render(hint, True, (200, 200, 200))
        window.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT // 2 + 50))

        countdown_surf = font_small.render(f"Game resumes in: {remaining:.1f} s", True, (255, 255, 255))
        window.blit(countdown_surf, (WIDTH // 2 - countdown_surf.get_width() // 2, HEIGHT // 2 + 90))

        pygame.display.update()

        if elapsed >= duration:
            captured = inputHandling.getBPM()
            measured_bpm = captured if captured > 0 else 60  # fallback to 60 BPM
            break

    # 3-second get-ready countdown
    countdown_start = time.time()
    countdown_duration = 3
    while True:
        elapsed = time.time() - countdown_start
        remaining = max(0.0, countdown_duration - elapsed)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit

        window.fill((0, 0, 0))
        window.blit(background_img, (0, 0))

        ready_surf = font_title.render("GET READY!", True, (255, 255, 0))
        window.blit(ready_surf, (WIDTH // 2 - ready_surf.get_width() // 2, HEIGHT // 2 - 60))

        num_surf = font_bpm.render(str(math.ceil(remaining)), True, (255, 255, 255))
        window.blit(num_surf, (WIDTH // 2 - num_surf.get_width() // 2, HEIGHT // 2 + 10))

        pygame.display.update()

        if elapsed >= countdown_duration:
            break

    mixer.music.unpause()


def init_game():
    global pause_sound
    global level_up_sound
    global game_over_sound
    global weapon_annihilation_sound

    pause_sound = mixer.Sound("res/sounds/pause.wav")
    level_up_sound = mixer.Sound("res/sounds/1up.wav")
    game_over_sound = mixer.Sound("res/sounds/gameover.wav")
    weapon_annihilation_sound = mixer.Sound("res/sounds/annihilation.wav")

    # player
    player_img_path = "res/images/spaceship.png"  # 64 x 64 px image
    player_width = 64
    player_height = 64
    player_x = (WIDTH / 2) - (player_width / 2)
    player_y = (HEIGHT / 10) * 9 - (player_height / 2)
    player_dx = initial_player_velocity
    player_dy = 0
    player_kill_sound_path = "res/sounds/explosion.wav"

    global player
    player = Player(player_img_path, player_width, player_height, player_x, player_y, player_dx, player_dy,
                    player_kill_sound_path)

    # bullet
    bullet_img_path = "res/images/bullet.png"  # 32 x 32 px image
    bullet_width = 32
    bullet_height = 32
    bullet_x = player_x + player_width / 2 - bullet_width / 2
    bullet_y = player_y + bullet_height / 2
    bullet_dx = 0
    bullet_dy = weapon_shot_velocity
    bullet_fire_sound_path = "res/sounds/gunshot.wav"

    global bullet, bullets
    bullet = Bullet(bullet_img_path, bullet_width, bullet_height, bullet_x, bullet_y, bullet_dx, bullet_dy,
                    bullet_fire_sound_path)
    bullets.clear()
    for _ in range(MAX_BULLETS):
        b = Bullet(bullet_img_path, bullet_width, bullet_height, bullet_x, bullet_y, bullet_dx, bullet_dy,
                   bullet_fire_sound_path)
        b.fired = False
        bullets.append(b)

    # enemy
    enemy_img_path = "res/images/enemy.png"  # 64 x 64 px image
    enemy_width = 64
    enemy_height = 64
    enemy_dx = initial_enemy_velocity
    enemy_dy = (HEIGHT / 10) / 2
    enemy_kill_sound_path = "res/sounds/enemykill.wav"

    # laser beam (equals number of enemies and retains corresponding enemy position)
    laser_img_path = "res/images/beam.png"  # 24 x 24 px image
    laser_width = 24
    laser_height = 24
    laser_dx = 0
    laser_dy = weapon_shot_velocity * 0.25
    shoot_probability = 0.3
    relaxation_time = 100
    laser_beam_sound_path = "res/sounds/laser.wav"

    global enemies
    global lasers
    global dive_bombers

    enemies.clear()
    lasers.clear()
    dive_bombers.clear()

    arc_enemy_count = min(level, MAX_ARC_ENEMIES)
    for _ in range(arc_enemy_count):
        enemy_x = random.randint(0, int(WIDTH - enemy_width))
        enemy_y = random.randint(int((HEIGHT / 10) * 1 - (enemy_height / 2)), int((HEIGHT / 10) * 4 - (enemy_height / 2)))
        laser_x = enemy_x + enemy_width / 2 - laser_width / 2
        laser_y = enemy_y + laser_height / 2

        enemy_obj = Enemy(enemy_img_path, enemy_width, enemy_height, enemy_x, enemy_y, enemy_dx, enemy_dy,
                          enemy_kill_sound_path)
        enemies.append(enemy_obj)

        laser_obj = Laser(laser_img_path, laser_width, laser_height, laser_x, laser_y, laser_dx, laser_dy,
                          shoot_probability, relaxation_time, laser_beam_sound_path)
        lasers.append(laser_obj)

    # dive bombers -- keep count capped; scale speed with level instead of spawning more
    dive_bomber_img_path = "res/images/alien.png"
    dive_bomber_width = 64
    dive_bomber_height = 64
    dive_bomber_dy = initial_enemy_velocity * 1.5 * (1.0 + (level - 1) * 0.2)
    dive_bomber_kill_sound_path = "res/sounds/enemykill.wav"
    for _ in range(MAX_DIVE_BOMBERS):
        db_x = random.randint(0, int(WIDTH - dive_bomber_width))
        db_y = random.randint(-dive_bomber_height * 4, -dive_bomber_height)
        db = DiveBomber(dive_bomber_img_path, dive_bomber_width, dive_bomber_height,
                        db_x, db_y, dive_bomber_dy, dive_bomber_kill_sound_path)
        dive_bombers.append(db)


# init game
init_game()
init_background_music()
measure_heartrate_screen()  # measure BPM before level 1 begins
runned_once = False
previous_frame_time = time.time()

# main game loop begins
while running:
    # start of frame timing
    start_time = time.time()
    raw_delta_time = start_time - previous_frame_time
    previous_frame_time = start_time
    # Clamp very large frame gaps so one hitch does not cause huge movement jumps.
    delta_time = min(max(raw_delta_time, 0.0), 0.1)
    frame_scale = delta_time * BASE_FPS
    bullet_frame_scale = max(raw_delta_time, 0.0) * BASE_FPS
    # print("heart rate:", inputHandling.getBPM())

    # background
    window.fill((0, 0, 0))
    window.blit(background_img, (0, 0))

    # register events
    for event in pygame.event.get():
        # Quit Event
        if event.type == pygame.QUIT:
            running = False

        # Keypress Down Event
        if event.type == pygame.KEYDOWN:
            # Left Arrow Key down
            if event.key == pygame.K_LEFT:
                print("LOG: Left Arrow Key Pressed Down")
                LEFT_ARROW_KEY_PRESSED = 1
            # Right Arrow Key down
            if event.key == pygame.K_RIGHT:
                print("LOG: Right Arrow Key Pressed Down")
                RIGHT_ARROW_KEY_PRESSED = 1
            # Up Arrow Key down
            if event.key == pygame.K_UP:
                print("LOG: Up Arrow Key Pressed Down")
                UP_ARROW_KEY_PRESSED = 1
            # Space Bar down
            if event.key == pygame.K_SPACE:
                print("LOG: Space Bar Pressed Down")
                SPACE_BAR_PRESSED = 1
            # Enter Key down ("Carriage RETURN key" from old typewriter lingo)
            if event.key == pygame.K_RETURN:
                print("LOG: Enter Key Pressed Down")
                ENTER_KEY_PRESSED = 1
                pause_state += 1
            # Esc Key down
            if event.key == pygame.K_ESCAPE:
                print("LOG: Escape Key Pressed Down - Closing Game")
                running = False
            if event.key == pygame.K_F11:
                print("LOG: F11 Pressed - Toggle Fullscreen")
                toggle_fullscreen()
                previous_frame_time = time.time()
            if event.key == pygame.K_t:
                use_measured_position = not use_measured_position

        # Keypress Up Event
        if event.type == pygame.KEYUP:
            # Right Arrow Key up
            if event.key == pygame.K_RIGHT:
                print("LOG: Right Arrow Key Released")
                RIGHT_ARROW_KEY_PRESSED = 0
            # Left Arrow Key up
            if event.key == pygame.K_LEFT:
                print("LOG: Left Arrow Key Released")
                LEFT_ARROW_KEY_PRESSED = 0
            # Up Arrow Key up
            if event.key == pygame.K_UP:
                print("LOG: Up Arrow Key Released")
                UP_ARROW_KEY_PRESSED = 0
            # Space Bar up
            if event.key == pygame.K_SPACE:
                print("LOG: Space Bar Released")
                SPACE_BAR_PRESSED = 0
            # Enter Key up ("Carriage RETURN key" from old typewriter lingo)
            if event.key == pygame.K_RETURN:
                print("LOG: Enter Key Released")
                ENTER_KEY_PRESSED = 0
            # Esc Key up
            if event.key == pygame.K_ESCAPE:
                print("LOG: Escape Key Released")
                ESC_KEY_PRESSED = 0

    # LEFT_ARROW_KEY_PRESSED, RIGHT_ARROW_KEY_PRESSED = inputHandling.getPresses()

    # check for pause game event
    if pause_state == 2:
        pause_state = 0
        runned_once = False
        mixer.music.unpause()
    if pause_state == 1:
        if not runned_once:
            runned_once = True
            pause_game()
        continue
    # manipulate game objects based on events and player actions
    # player spaceship movement
    if RIGHT_ARROW_KEY_PRESSED or inputHandling.getPresses()[1]:
        player.setpoint += player.dx * frame_scale
    if LEFT_ARROW_KEY_PRESSED or inputHandling.getPresses()[0]:
        player.setpoint -= player.dx * frame_scale
    # bullet firing — automatic, rate driven by measured heart rate
    # fire_interval is the time (seconds) between shots = 60 / BPM
    fire_interval = ((60.0 / measured_bpm) if measured_bpm > 0 else 1.0)/2
    # print(fire_interval)
    current_time = time.time()
    if (current_time - last_bullet_time) >= fire_interval:
        inactive = next((b for b in bullets if not b.fired), None)
        if inactive is not None:
            inactive.fired = True
            inactive.fire_sound.play()
            inactive.x = player.x + player.width / 2 - inactive.width / 2
            inactive.y = player.y + inactive.height / 2
            last_bullet_time = current_time
    # bullet movement
    for b in bullets:
        if b.fired:
            b.y -= b.dy * bullet_frame_scale

    # dive bomber movement
    for db in dive_bombers:
        db.y += db.dy * (1.0 + (difficulty - 1) * 0.15) * frame_scale

    # iter through every enemies and lasers
    for i in range(len(enemies)):
        # laser beaming
        if not lasers[i].beamed:
            lasers[i].shoot_timer += delta_time
            if lasers[i].shoot_timer >= lasers[i].relaxation_time:
                lasers[i].shoot_timer = 0.0
                random_chance = random.randint(0, 100)
                if random_chance <= (lasers[i].shoot_probability * 100):
                    lasers[i].beamed = True
                    lasers[i].beam_sound.play()
                    lasers[i].x = enemies[i].x + enemies[i].width / 2 - lasers[i].width / 2
                    lasers[i].y = enemies[i].y + lasers[i].height / 2
        # enemy movement — fly in a curved arc across the screen and then restart from off-screen
        speed_multiplier = 1.0 + (difficulty - 1) * 0.15
        enemies[i].move_in_arc(speed_multiplier, frame_scale)
        # laser movement
        if lasers[i].beamed:
            lasers[i].y += lasers[i].dy * frame_scale

    # collision check
    for i in range(len(enemies)):
        for b in bullets:
            if b.fired and collision_check(b, enemies[i]):
                kill_enemy(player, b, enemies[i])
                break

    for i in range(len(lasers)):
        laser_player_collision = collision_check(lasers[i], player)
        if laser_player_collision:
            kill_player(player, enemies[i], lasers[i])

    for i in range(len(enemies)):
        enemy_player_collision = collision_check(enemies[i], player)
        if enemy_player_collision:
            kill_enemy(player, bullets[0], enemies[i])
            kill_player(player, enemies[i], lasers[i])

    for i in range(len(lasers)):
        for b in bullets:
            if b.fired and collision_check(b, lasers[i]):
                destroy_weapons(player, b, enemies[i], lasers[i])
                break

    # dive bomber collisions
    for db in dive_bombers:
        # bullet destroys dive bomber
        for b in bullets:
            if b.fired and collision_check(b, db):
                b.fired = False
                db.kill_sound.play()
                db.respawn()
                break
        # dive bomber touches player
        if collision_check(db, player):
            db.kill_sound.play()
            db.respawn()
            life -= 1
            print("Life Left:", life)
            if life <= 0:
                gameover()
        # dive bomber reaches bottom of screen
        elif db.y > HEIGHT:
            db.respawn()
            life -= 1
            print("Life Left:", life)
            if life <= 0:
                gameover()

    # boundary check: 0 <= x <= WIDTH, 0 <= y <= HEIGHT
    # player spaceship
    if player.setpoint < 0:
        player.setpoint = 0
    if player.setpoint > WIDTH - player.width:
        player.setpoint = WIDTH - player.width

    if use_measured_position:
        player.x = inputHandling.getHoogte()*(WIDTH-player.width)/max_hoogte
    else:
        player.x = player.setpoint

    if current_time - last_setpoint_time >= 0.1:
        inputHandling.sendSetpoint((player.setpoint + player.width / 2)*max_hoogte/(WIDTH-player.width))
        last_setpoint_time = current_time
    # bullet
    for b in bullets:
        if b.y < 0:
            b.fired = False
            b.x = player.x + player.width / 2 - b.width / 2
            b.y = player.y + b.height / 2
    # laser
    for i in range(len(lasers)):
        if lasers[i].y > HEIGHT:
            lasers[i].beamed = False
            lasers[i].x = enemies[i].x + enemies[i].width / 2 - lasers[i].width / 2
            lasers[i].y = enemies[i].y + lasers[i].height / 2

    # create frame by placing objects on the surface
    scoreboard()
    for laser in lasers:
        laser.draw()
    for enemy in enemies:
        enemy.draw()
    for db in dive_bombers:
        db.draw()
    for b in bullets:
        b.draw()
    player.draw()

    # render the display
    pygame.display.update()

    # end of rendering, end on a frame
    frame_count += 1
    end_time = time.time()
    single_frame_rendering_time = end_time - start_time
    # fps = 1 / render_time

    total_time = total_time + single_frame_rendering_time
    if total_time >= 1.0:
        fps = frame_count
        frame_count = 0
        total_time = 0
    # print("rendering time:", single_frame_rendering_time)
    # print("FPS:", fps)
