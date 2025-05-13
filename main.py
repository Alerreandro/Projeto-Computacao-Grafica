import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random
from PIL import Image

# Constantes do jogo e da janela
MAZE_SIZE = 14          # Tamanho do labirinto (número de células em cada dimensão)
PLAYER_RADIUS = 0.2     # Raio do jogador para detecção de colisões
SCREEN_WIDTH = 1080     # Largura da janela do jogo
SCREEN_HEIGHT = 720     # Altura da janela do jogo
MOUSE_SENSITIVITY = 0.12  # Sensibilidade do mouse para a rotação da câmera
PLAYER_SPEED = 0.1      # Velocidade de movimento do jogador

# Classe que representa o labirinto
class Maze:
    def __init__(self, size):
        self.size = size
        self.grid = self.generate_maze()  # Cria o labirinto utilizando algoritmo de busca em profundidade
        self.portal_pos = self.find_valid_portal_position()  # Determina uma posição válida para o portal

    # Gera o labirinto usando o algoritmo de backtracking (busca em profundidade)
    def generate_maze(self):
        # Inicializa uma matriz preenchida com 1's (paredes)
        maze = np.ones((self.size, self.size), dtype=int)
        # Define o ponto de início do labirinto
        stack = [(1, 1)]
        maze[1, 1] = 0  # Marca o ponto inicial como caminho (0)

        while stack:
            x, y = stack[-1]
            # Lista de vizinhos a serem visitados (movimentos de 2 em 2 para criar corredores)
            neighbors = [(x + dx, y + dy) for dx, dy in [(0, 2), (0, -2), (2, 0), (-2, 0)]]
            # Filtra vizinhos dentro dos limites e que ainda são paredes
            neighbors = [(nx, ny) for nx, ny in neighbors if 0 < nx < self.size - 1 and 0 < ny < self.size - 1 and maze[nx, ny] == 1]

            if neighbors:
                # Escolhe um vizinho aleatório para visitar
                nx, ny = random.choice(neighbors)
                # Remove a parede intermediária entre o nó atual e o escolhido
                maze[(x + nx) // 2, (y + ny) // 2] = 0
                # Marca o vizinho como caminho
                maze[nx, ny] = 0
                # Adiciona o vizinho na pilha para continuar a exploração
                stack.append((nx, ny))
            else:
                # Se não houver vizinhos disponíveis, retrocede (backtracking)
                stack.pop()

        return maze

    # Encontra uma posição válida para posicionar o portal (onde não há parede)
    def find_valid_portal_position(self):
        """Encontra uma posição válida para o portal (onde não há parede)."""
        # Percorre a grade em ordem decrescente para posicionar o portal em uma área mais distante do início
        for x in range(self.size - 1, 0, -1):
            for z in range(self.size - 1, 0, -1):
                if self.grid[x][z] == 0:  # Se for caminho, retorna essa posição
                    return (x, z)
        return (1, 1)  # Fallback: se não encontrar, retorna a posição inicial

    # Desenha o labirinto, aplicando a textura da parede para cada célula com valor 1
    def draw(self, wall_texture):
        glBindTexture(GL_TEXTURE_2D, wall_texture)
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x][y] == 1:
                    self.draw_textured_cube(x, 0, y)

    # Desenha um cubo texturizado representando uma parede
    def draw_textured_cube(self, x, y, z):
        size = 1  # Tamanho de cada célula
        # Define os 8 vértices do cubo
        vertices = [
            (x, y, z), (x + size, y, z), (x + size, y, z + size), (x, y, z + size),
            (x, y + size, z), (x + size, y + size, z), (x + size, y + size, z + size), (x, y + size, z + size)
        ]
        # Define as 6 faces do cubo utilizando os índices dos vértices
        faces = [
            (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
            (2, 3, 7, 6), (0, 3, 7, 4), (1, 2, 6, 5)
        ]
        # Coordenadas de textura para cada vértice da face
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 1)]

        glBegin(GL_QUADS)
        for face in faces:
            for i, vertex in enumerate(face):
                glTexCoord2fv(tex_coords[i % 4])
                glVertex3fv(vertices[vertex])
        glEnd()

    # Desenha o portal utilizando a textura fornecida
    def draw_portal(self, portal_texture):
        x, z = self.portal_pos
        glBindTexture(GL_TEXTURE_2D, portal_texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(x, 0, z)
        glTexCoord2f(1, 0)
        glVertex3f(x + 1, 0, z)
        glTexCoord2f(1, 1)
        glVertex3f(x + 1, 1, z)
        glTexCoord2f(0, 1)
        glVertex3f(x, 1, z)
        glEnd()

# Classe que representa a câmera (ou jogador) e lida com seu movimento
class Camera:
    def __init__(self, maze):
        # Posição inicial da câmera
        self.x, self.y, self.z = 1.5, 0.5, 1.5
        self.angle_yaw = 0  # Ângulo de rotação no eixo horizontal
        self.maze = maze  # Referência ao labirinto para verificação de colisões

    # Verifica se o jogador pode se mover para uma nova posição, checando colisões com as paredes
    def can_move(self, new_x, new_z):
        maze_x, maze_z = int(new_x), int(new_z)
        # Verifica se a posição está dentro dos limites e se é um caminho (0)
        if 0 <= maze_x < len(self.maze.grid) and 0 <= maze_z < len(self.maze.grid[0]) and self.maze.grid[maze_x][maze_z] == 0:
            # Checa as bordas do jogador para evitar colisões com paredes próximas
            for dx in [-PLAYER_RADIUS, PLAYER_RADIUS]:
                for dz in [-PLAYER_RADIUS, PLAYER_RADIUS]:
                    check_x, check_z = new_x + dx, new_z + dz
                    if self.maze.grid[int(check_x)][int(check_z)] == 1:
                        return False
            return True
        return False

    # Move a câmera de acordo com os deslocamentos dx e dz, verificando colisões
    def move(self, dx, dz):
        new_x, new_z = self.x + dx, self.z + dz
        if self.can_move(new_x, self.z):
            self.x = new_x
        if self.can_move(self.x, new_z):
            self.z = new_z

    # Rotaciona a câmera alterando o ângulo de visão
    def rotate(self, angle):
        self.angle_yaw += angle

    # Aplica a transformação de visualização (define a posição e direção da câmera)
    def apply(self):
        glLoadIdentity()
        gluLookAt(self.x, self.y, self.z,
                  self.x + np.cos(np.radians(self.angle_yaw)), self.y, self.z + np.sin(np.radians(self.angle_yaw)),
                  0, 1, 0)

    # Verifica se a câmera colidiu com o portal
    def check_portal_collision(self, portal_pos):
        portal_x, portal_z = portal_pos
        distance = np.sqrt((self.x - portal_x) ** 2 + (self.z - portal_z) ** 2)
        return distance < 0.5  # Considera colisão se estiver a uma distância menor que 0.5

# Função para carregar uma textura a partir de um arquivo
def load_texture(filename):
    # Abre a imagem e converte para RGBA para garantir transparência se necessário
    img = Image.open(filename).convert("RGBA")
    # Corrige a inversão vertical da imagem
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    # Converte a imagem para um array NumPy
    img_data = np.array(img, dtype=np.uint8)

    # Gera um ID para a textura e a configura
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    # Define parâmetros de filtragem e de repetição da textura
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    # Define a imagem da textura
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

    return texture_id

# Configuração inicial do OpenGL para o jogo
def setup_opengl():
    glEnable(GL_DEPTH_TEST)   # Habilita teste de profundidade para renderização 3D correta
    glEnable(GL_TEXTURE_2D)   # Habilita mapeamento de texturas
    glMatrixMode(GL_PROJECTION)
    # Define a perspectiva (campo de visão, proporção, plano próximo e distante)
    gluPerspective(60, (SCREEN_WIDTH / SCREEN_HEIGHT), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

# Desenha o chão do labirinto com a textura fornecida
def draw_floor(floor_texture):
    size = MAZE_SIZE
    glBindTexture(GL_TEXTURE_2D, floor_texture)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex3f(0, 0, 0)
    glTexCoord2f(1, 0)
    glVertex3f(size, 0, 0)
    glTexCoord2f(1, 1)
    glVertex3f(size, 0, size)
    glTexCoord2f(0, 1)
    glVertex3f(0, 0, size)
    glEnd()

# Função que trata os eventos do Pygame (entrada do usuário)
def handle_events(camera):
    for event in pygame.event.get():
        # Se o usuário fechar a janela ou pressionar ESC, encerra o jogo
        if event.type == QUIT or pygame.key.get_pressed()[K_ESCAPE]:
            return False
        # Se o mouse se mover, a câmera é rotacionada conforme o movimento horizontal
        if event.type == pygame.MOUSEMOTION:
            x, y = event.rel
            camera.rotate(x * MOUSE_SENSITIVITY)
    return True

# Exibe o menu inicial do jogo
def show_menu():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    font = pygame.font.Font(None, 74)
    title_text = font.render("Jogo do Labirinto", True, (255, 255, 255))
    start_text = pygame.font.Font(None, 50).render("Pressione ESPAÇO para começar", True, (255, 255, 255))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(title_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 100))
        screen.blit(start_text, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 50))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                exit()  # Fecha o jogo corretamente
            # Ao pressionar a barra de espaço, sai do menu e inicia o jogo
            if event.type == KEYDOWN and event.key == K_SPACE:
                return

# Exibe a tela de vitória quando o jogador encontra o portal
def show_win_screen():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    font = pygame.font.Font(None, 74)
    win_text = font.render("Você encontrou o portal! Parabéns!", True, (255, 255, 255))
    restart_text = pygame.font.Font(None, 50).render("Pressione R para reiniciar ou ESC para sair", True, (255, 255, 255))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(win_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 50))
        screen.blit(restart_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 + 50))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                exit()
            # Se o usuário pressionar 'R', o jogo será reiniciado
            if event.type == KEYDOWN:
                if event.key == K_r:
                    return True  # Indica que o jogo deve reiniciar
                if event.key == K_ESCAPE:
                    return False  # Indica que o jogo deve fechar

# Função principal que inicializa e executa o loop do jogo
def main():
    pygame.init()

    show_menu()  # Exibe o menu inicial antes de começar o jogo

    # Inicializa a janela com suporte a OpenGL e double buffering
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.mouse.set_visible(False)  # Esconde o cursor do mouse
    pygame.event.set_grab(True)       # Captura o mouse para que ele não saia da janela
    clock = pygame.time.Clock()

    # Inicializa o mixer para tocar sons
    pygame.mixer.init()
    portal_sound = pygame.mixer.Sound("win.wav")  # Carrega o som de vitória

    setup_opengl()  # Configura as propriedades do OpenGL
    maze = Maze(MAZE_SIZE)  # Cria o labirinto
    camera = Camera(maze)   # Cria a câmera vinculada ao labirinto

    # Carrega as texturas para o chão, paredes e portal
    floor_texture = load_texture("chao.jpg")
    wall_texture = load_texture("parede.jpg")
    portal_texture = load_texture("portal.jpg")

    running = True
    while running:
        # Trata os eventos de entrada (teclado, mouse)
        running = handle_events(camera)

        # Movimentação do jogador utilizando as teclas W, A, S, D
        keys = pygame.key.get_pressed()
        if keys[K_w]:
            camera.move(PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)),
                        PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)))
        if keys[K_s]:
            camera.move(-PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)),
                        -PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)))
        if keys[K_a]:
            camera.move(PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)),
                        -PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)))
        if keys[K_d]:
            camera.move(-PLAYER_SPEED * np.sin(np.radians(camera.angle_yaw)),
                        PLAYER_SPEED * np.cos(np.radians(camera.angle_yaw)))

        # Limpa os buffers de cor e profundidade
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        camera.apply()  # Aplica a transformação de visualização da câmera

        # Desenha o chão, o labirinto (paredes) e o portal
        draw_floor(floor_texture)
        maze.draw(wall_texture)
        maze.draw_portal(portal_texture)

        # Verifica se houve colisão do jogador com o portal
        if camera.check_portal_collision(maze.portal_pos):
            portal_sound.play()  # Toca o som de vitória
            # Exibe a tela de vitória e reinicia ou finaliza o jogo conforme a escolha do jogador
            if show_win_screen():
                return main()  # Reinicia o jogo chamando a função main novamente
            else:
                running = False  # Encerra o loop do jogo

        pygame.display.flip()  # Atualiza a tela
        clock.tick(60)         # Limita a taxa de quadros para 60 FPS
        # Reposiciona o mouse no centro da tela para evitar deslocamentos acumulados
        pygame.mouse.set_pos((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

    pygame.quit()  # Encerra o Pygame ao sair do loop

# Executa a função principal se o script for executado diretamente
if __name__ == "__main__":
    main()
