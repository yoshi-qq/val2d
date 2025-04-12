import pygame, os, time, math, threading, ctypes
from screeninfo import get_monitors
from pygame.locals import HWSURFACE, DOUBLEBUF, FULLSCREEN
from ctypes.wintypes import HWND, HANDLE, UINT, HGLOBAL, LPVOID

HD = (1920, 1080)
QHD = (2560, 1440)
FOUR_K = (3840, 2160)

activeInput = None
running = False
clickEvent = False
defaultFont = None
sprites = {}
keys = set()
exeKeys = set()



def preload(file, nativeRes = (1920, 1080), scale = 1, windowRes = False):
    global root, displayResolution, nativeResolution, middle, rx, ry, xMultiplier, yMultiplier
    root = os.path.dirname(os.path.abspath(file))
    nativeResolution = nativeRes
    displayResolution = nativeResolution
    middle = (displayResolution[0]/2, displayResolution[1]/2)
    if windowRes == False:
        for monitor in get_monitors():
            if monitor.is_primary:
                displayResolution = (monitor.width*scale, monitor.height*scale)
                break
    else:
        displayResolution = windowRes
    xMultiplier, yMultiplier = displayResolution[0]/nativeResolution[0], displayResolution[1]/nativeResolution[1]
    if singleSize:
        rx, ry = xMultiplier, yMultiplier
    else:
        rx, ry = 1, 1
    
def paperclipInit():
    global getClipboard
    OpenClipboard = ctypes.windll.user32.OpenClipboard
    OpenClipboard.argtypes = HWND,
    OpenClipboard.restype = ctypes.c_bool
    CloseClipboard = ctypes.windll.user32.CloseClipboard
    GetClipboardData = ctypes.windll.user32.GetClipboardData
    GetClipboardData.argtypes = UINT,
    GetClipboardData.restype = HANDLE
    GlobalLock = ctypes.windll.kernel32.GlobalLock
    GlobalLock.argtypes = HGLOBAL,
    GlobalLock.restype = LPVOID
    GlobalUnlock = ctypes.windll.kernel32.GlobalUnlock
    GlobalUnlock.argtypes = HGLOBAL,

    CF_UNICODETEXT = 13

    def getClipboard():
        text = ""
        if OpenClipboard(None):
            h_clip_mem = GetClipboardData(CF_UNICODETEXT)
            if h_clip_mem:
                text_ptr = GlobalLock(h_clip_mem)
                if text_ptr:
                    text = ctypes.c_wchar_p(text_ptr).value
                    GlobalUnlock(h_clip_mem)
            CloseClipboard()
        return text

def init(file = __file__, fps: int = 30, fontPath = "Arial", fullscreen = False, singleSizeOn = False, windowName = "GRAPHY!", spriteFolder = "assets", spriteExtension = ".png", scale = 1, nativeRes = (1920, 1080), windowIcon = "icon", windowRes = False):
    global sprites, screen, realScreen, renders, clock, nativeResolution, singleSize, running, defaultFont, FPS
    FPS = fps
    nativeResolution = nativeRes
    singleSize = singleSizeOn
    defaultFont = fontPath
    preload(file, nativeResolution, scale, windowRes)
    paperclipInit()
    pygame.init()
    pygame.display.set_caption(windowName)
    if fullscreen:
        flags = HWSURFACE | DOUBLEBUF | FULLSCREEN
    else:
        flags = HWSURFACE | DOUBLEBUF
    if not singleSize:
        screen = pygame.surface.Surface((nativeResolution[0], nativeResolution[1]), flags)
        realScreen = pygame.display.set_mode((displayResolution[0], displayResolution[1]), flags)
    else:
        screen = pygame.display.set_mode((displayResolution[0], displayResolution[1]), flags)
    classes()
    renders = []
    spriteRoot = os.path.join(root, spriteFolder)
    sprites = {}
    scanDirectory(spriteRoot, spriteExtension)
    try:
        pygame.display.set_icon(sprites[windowIcon][0])
    except: pass
    clock = pygame.time.Clock()
    running = True

def scanDirectory(directory, extension = ".png", extra = ""):
    for file in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, file)):
            scanDirectory(os.path.join(directory, file), extension, f"{extra}/{file}")
        elif file.endswith(extension):
            image = pygame.image.load(os.path.join(directory, file))
            if image.get_alpha() is None:
                image = image.convert()
                scaler = 4
                image = pygame.transform.scale(image, (round(image.get_width()*rx*scaler), round(image.get_height()*ry*scaler)))
                sprites[file.replace(extension, "").rstrip(".")] = (image, extra, False)
            else:
                image = image.convert_alpha()
                scaler = 4
                image = pygame.transform.scale(image, (round(image.get_width()*rx*scaler), round(image.get_height()*ry*scaler)))
                sprites[file.replace(extension, "").rstrip(".")] = (image, extra, True)

def drawNormal(surface, img, x = 0, y = 0, width = 1, height = 1, middle = False):
    global sprites
    x, y, width, height = round(x*rx), round(y*ry), width*rx, height*ry
    if abs(img.get_height() - height) > 1 or abs(img.get_width() - width) > 1:
        img = pygame.transform.scale(img, (width, height))
    topleft = (x, y)
    if middle:
        topleft = (x - img.get_width()/2, y - img.get_height()/2)
    surface.blit(img, topleft)

def drawRotated(surface, img, x = 0, y = 0, angle = 180, width = 1, height = 1, stretch = 1, middle = False):
    width, height = width*rx, height*ry
    if abs(img.get_height() - height/stretch) > 1 or abs(img.get_width() - width*stretch) > 1:
        img = pygame.transform.scale(img, (width*stretch, height/stretch))
    if angle == 0:
        drawNormal(surface, img, x, y, width, height, middle)
        return
    elif angle == "flip":
        img = pygame.transform.flip(img, False, True)
    elif angle == 180:
        img = pygame.transform.flip(img, True, True)
    else:
        if abs(img.get_height() - height) > 1 or abs(img.get_width() - width) > 1:
            img = pygame.transform.scale(img, (width, height))
        center = img.get_rect().center
        img = pygame.transform.rotate(img, -1*angle)
        rotated_rect = img.get_rect()
        rotated_rect.center = center
        offset_x = rotated_rect.x - surface.get_rect().x
        offset_y = rotated_rect.y - surface.get_rect().y
        x += offset_x*0.75
        y += offset_y*0.75
    x, y = round(x*rx), round(y*ry)
    topleft = (x, y)
    if middle:
        topleft = (x - img.get_width()/2, y - img.get_height()/2)
    surface.blit(img, topleft)

def getMouse():
    return (pygame.mouse.get_pos()[0]/xMultiplier, pygame.mouse.get_pos()[1]/yMultiplier)

def click():
    global clickEvent
    clickEvent = True

def keyPress(key):
    global keys, activeInput
    if activeInput is not None:
        if key == pygame.K_SPACE:
            activeInput.text += " "
            activeInput.update()
        elif key == pygame.K_BACKSPACE:
            activeInput.text = activeInput.text[:-1]
            activeInput.update()

def pressDelay(key, delay = 0.25):
    global keys, exeKeys
    time.sleep(delay)
    if key in keys:
        exeKeys.add(key)

def preDraw():
    pass

def postDraw():
    pass

def draw():
    global clickEvent, renders, running, keys, FPS
    if not running:
        raise Exception ("Pygame not initialized\nPlease call graphy.init() before graphy.draw()")
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit();
            return;
        elif event.type == pygame.MOUSEBUTTONDOWN:
            click();
        elif event.type == pygame.KEYDOWN:
            if activeInput is not None:
                if (event.key == pygame.K_v) and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    activeInput.text += getClipboard()
                    activeInput.update()
                elif activeInput is not None and event.unicode and event.key not in (pygame.K_BACKSPACE, pygame.K_SPACE, pygame.K_RETURN):
                    activeInput.text += event.unicode
                    activeInput.update()
                else:
                    keys.add(event.key)
                    threading.Thread(target = pressDelay, args = (event.key, 0.25)).start()
                    keyPress(event.key)
        elif event.type == pygame.KEYUP:
            keys.discard(event.key)
            try:
                exeKeys.discard(event.key)
            except: pass
        elif event.type == pygame.KEYDOWN:
            keyPress(event.key)
            
    for key in exeKeys:
        keyPress(key)
                
                
    screen.fill((50, 50, 50))
    renders.sort(key = lambda render: render.priority + render.priorityOffset)
    preDraw()
    hoverable = True
    for render in renders[::-1]:
        if render.enabled:
            instances = (isinstance(render, RenderButton), isinstance(render, RenderInput), isinstance(render, RenderTextButton))
            if any(instances):
                if hoverable and pointInRect(getMouse(), (render.x, render.y, render.width, render.height), render.angle, render.middle):
                    render.hover(True)
                    if clickEvent:
                        render.click(True)
                    hoverable = False
                else:
                    render.hover(False)
                    if clickEvent and instances[1]:
                        render.click(False)
                        
    for render in renders:
        if render.enabled:
            render.draw()  
        if render.temporary:
            renders.remove(render)

    clicked = not clickEvent
    clickEvent = False
    postDraw()
    if not singleSize:
        realScreen.blit(pygame.transform.scale(screen, (displayResolution[0], displayResolution[1])), (0, 0))
    pygame.display.flip()
    clock.tick(FPS)
    return clicked

def renderThis(renderObject):
    pass

#future use
def rectOverlap(rect1, rect2):
    l1 = Point(rect1[0],rect1[1])
    r1 = Point(rect1[0]+rect1[2], rect1[1]+rect1[3])
    l2 = Point(rect2[0],rect2[1])
    r2 = Point(rect2[0]+rect2[2], rect2[1]+rect2[3])
    
    # if rectangle has area 0, no overlap
    if l1.x == r1.x or l1.y == r1.y or r2.x == l2.x or l2.y == r2.y:
        return False
     
    # If one rectangle is on left side of other
    if l1.x > r2.x or l2.x > r1.x:
        return False
 
    # If one rectangle is above other
    if r1.y < l2.y or r2.y < l1.y:
        return False
 
    return True 

def markthis(size = 10):
    x, y = pygame.mouse.get_pos()
    RenderImage(imageName = "mark", x = x/rx, y = y/ry, surface = screen, priority=10, width = size, height = size, middle = True)

def rotate_point_around_center(point, center, angle_degrees):
    """Rotate a point around another point by a given angle in degrees, counter-clockwise."""
    angle_radians = math.radians(-angle_degrees)  # Negative for counter-clockwise rotation
    px, py = point
    cx, cy = center
    
    # Translate point back to origin:
    px -= cx
    py -= cy
    
    # Rotate point
    xnew = px * math.cos(angle_radians) - py * math.sin(angle_radians)
    ynew = px * math.sin(angle_radians) + py * math.cos(angle_radians)
    
    # Translate point back:
    px = xnew + cx
    py = ynew + cy
    return px, py

def pointInRect(mouse_pos, rect, angle_degrees = 0, middle = False):    
    rect_x, rect_y, rect_w, rect_h = rect
    if middle:
        rect_x -= rect_w/2
        rect_y -= rect_h/2
    center = (rect_x + rect_w / 2, rect_y + rect_h / 2)
    
    unrotated_mouse_pos = rotate_point_around_center(mouse_pos, center, angle_degrees)
    
    return (rect_x <= unrotated_mouse_pos[0] <= rect_x + rect_w and
            rect_y <= unrotated_mouse_pos[1] <= rect_y + rect_h)

def hex(hexString: str):
    if hexString[0] == "#":
        hexString = hexString[1:]
    colorTuple = tuple(int(hexString[0:2], 16), int(hexString[2:4], 16), int(hexString[4:6], 16))
    return colorTuple

def classes():
    global Sprite, Point, RenderObject, RenderImage, RenderAnimation, RenderButton, RenderText, RenderTextButton, RenderInput, GameObject

    class Sprite(pygame.sprite.Sprite):
        def __init__(self, image, position):
            super().__init__()
            self.image = image
            self.rect = self.image.get_rect(topleft=position)

    #future use
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            
    class RenderObject():
        def __init__(self, surface = screen, temporary = False, enabled = True, x = 0, xOffset = 0, y = 0, yOffset = 0, width = 10, height = 10, priority = 2, angle = 0, stretch = 1):
            self.enabled = enabled
            self.temporary = temporary
            self.x = x
            self.y = y
            self.xOffset = xOffset
            self.yOffset = yOffset
            self.width = width
            self.height = height
            self.sizeMulti = 1
            self.priority = priority
            self.priorityOffset = 0
            self.angle = angle
            self.stretch = stretch
            self.surface = surface
            
        def show(self):
            self.enabled = True
            
        def hide(self):
            self.enabled = False
            
        def remove(self):
            global renders
            renders.remove(self)
            
    class RenderImage(RenderObject):
        def __init__(self, strName = "image", surface = screen, temporary = False, enabled = True, imageName = None, x = 0, xOffset = 0, y = 0, yOffset = 0, width = 10, height = 10, middle = False, priority = 2, angle = 0, stretch = 1, mapPosition = (None, None), gen = True):
            self.strName = strName
            self.name = imageName
            self.imageName = imageName
            self.xOffset = xOffset
            self.yOffset = yOffset
            self.middle = middle
            self.sizeMulti = 1
            self.mapPosition = mapPosition
            if self.imageName is None:
                self.imageName = pygame.surface.Surface((width, height))
                self.imageName.fill((255, 0, 0))
            self.changeImage(self.imageName)
            super().__init__(surface = surface, temporary = temporary, enabled = enabled, x = x, y = y, width = width, height = height, priority = priority, angle = angle, stretch = stretch)
            if type(self) is RenderImage and gen:
                renders.append(self)
        
        def offset(self, x: float = None, y: float = None, size: float = None, priority = None):
            if x is not None:
                self.xOffset = x
            if y is not None:
                self.yOffset = y
            if size is not None:
                self.sizeMulti = size
            if priority is not None:
                self.priorityOffset = priority
        
        def update(self):
            try:
                self.image = sprites[self.image][0]
            except KeyError:
                self.image = self.image
        def draw(self):
            drawRotated(surface = self.surface, img = self.image, x = self.x + self.xOffset, y = self.y + self.yOffset, angle = self.angle, width = self.width * self.sizeMulti, height = self.height * self.sizeMulti, stretch = self.stretch, middle = self.middle)

        def changeImage(self, image):
            try:
                self.image = sprites[image][0]
            except KeyError:
                self.image = image
      
    class RenderAnimation(RenderImage):
        def __init__(self, continuous = True, slowdown = 1, rotation = 1, strName = "animation", surface = screen, temporary = False, enabled = True, imageNames: tuple = None, x = 0, xOffset = 0, y = 0, yOffset = 0, width = 10, height = 10, middle = False, priority = 2, angle = 0, stretch = 1, mapPosition = (None, None), gen = True):
            self.rotation = rotation
            self.continuous = continuous
            self.slowdown = slowdown
            self.imageNames = imageNames
            if imageNames is None:
                return
            self.frame = 0
            super().__init__(strName = strName, surface = surface, temporary = temporary, enabled = enabled, imageName = imageNames[0], x = x, xOffset = xOffset, y = y, yOffset = yOffset, width = width, height = height, middle = middle, priority = priority, angle = angle, stretch = stretch, mapPosition = mapPosition, gen = gen)
            
            if type(self) is RenderAnimation and gen:
                renders.append(self)
            
        def draw(self):
            if self.frame >= len(self.imageNames):
                if self.continuous:
                   self.frame = 0
                else:
                    self.remove()
                    return
            self.changeImage(self.imageNames[math.floor(self.frame)])
            super().draw()
            self.angle += self.rotation
            self.frame += self.slowdown**-1
        
    class RenderButton(RenderImage):
        def __init__(self, imageName: str = None, strName = "button", clickAction = False, hoverAction = False, unHoverAction = False, arguments: tuple = (), hoverArguments: tuple = (), unHoverArguments: tuple = (), surface = screen, temporary = False, enabled = True, hoverImageName = False, x = 0, xOffset = 0, y = 0, yOffset = 0, width = 10, height = 10, priority = 2, angle = 0, stretch = 1, middle = False, gen = True):
            if isinstance(clickAction, str): # define click action
                clickAction = eval(clickAction)  
            self.clickAction = clickAction
            self.arguments = arguments
            if isinstance(hoverAction, str): # define hover action
                hoverAction = eval(hoverAction) 
            self.hoverAction = hoverAction
            self.hoverArguments = hoverArguments
            if isinstance(unHoverAction, str): # define unhover action
                unHoverAction = eval(unHoverAction)  
            self.unHoverAction = unHoverAction
            self.unHoverArguments = unHoverArguments
            
            # define images
            self.hoverImageName = hoverImageName
            
            self.hovered = False
            
            super().__init__(strName = strName, surface = surface, temporary = temporary, enabled = enabled, imageName = imageName, x = x, xOffset = xOffset, y = y, yOffset = yOffset, width = width, height = height, priority = priority, angle = angle, stretch = stretch, middle = middle, gen = gen)
            if type(self) is RenderButton and gen:
                renders.append(self)
        
        def click(self, me):
            if self.clickAction != False:
                self.clickAction(*self.arguments)
        
        def hover(self, hover = False):
            if hover:
                if True:
                    self.hovered = True
                    if self.hoverImageName != False:
                        self.changeImage(self.hoverImageName)
                    if self.hoverAction != False:
                        self.hoverAction(*self.hoverArguments)
            elif self.hovered:
                self.hovered = False
                if self.hoverImageName != False:
                    self.changeImage(self.imageName)
                if self.unHoverAction != False:
                    self.unHoverAction(*self.unHoverArguments)
        
        def draw(self):
            return super().draw()
        
    class RenderText(RenderObject):
        def __init__(self, surface: pygame.surface = screen, enabled = True, x: int = 0, y: int = 0, xOffset: int = 0, yOffset: int = 0, text: str = "example", font: pygame.font = defaultFont, size: int = 30, color: tuple = (0, 0, 0), temporary = False, angle = 0, stretch = 1, middle = False, priority: float = 2, gen: bool = True):
            try:
                self.font = pygame.font.Font(font, size)
            except:
                self.font = pygame.font.SysFont(defaultFont, size)
            self.text = text
            self.color = color
            self.middle = middle
            self.renderSurface = self.font.render(text, True, color)
            self.height = self.renderSurface.get_height()
            self.width = self.renderSurface.get_width()
            super().__init__(surface = surface, temporary = temporary, enabled = enabled, x = x, y = y, width = self.width, height = self.height, priority = priority, angle = angle, stretch = stretch)
            if type(self) is RenderText and gen:
                    renders.append(self)
        
        def updateText(self, newText: str) -> None:
            self.text = newText
            self.renderSurface = self.font.render(self.text, True, self.color)
            self.height = self.renderSurface.get_height()
            self.width = self.renderSurface.get_width()
        
        def draw(self):
            drawRotated(surface = self.surface, img = self.renderSurface, x = self.x + self.xOffset, y = self.y + self.yOffset, angle = self.angle, width = self.width * self.sizeMulti, height = self.height * self.sizeMulti, stretch = self.stretch, middle = self.middle)

    class RenderTextButton(RenderButton):
        def __init__(self, surface: pygame.surface = screen, drawType = "rect", imageName = None, hoverImageName = None, strName = "textButton", enabled = True, x: int = 0, y: int = 0, width: int = 30, height: int = 10, xOffset: int = 0, yOffset: int = 0, clickAction = False, hoverAction = False, unHoverAction = False, arguments: tuple = (), hoverArguments: tuple = (), unHoverArguments: tuple = (),  text: str = "example", font: pygame.font = defaultFont, size: int = None, borderSize = 5, color: tuple = (0, 0, 0), activeColor: tuple = (100, 100, 100), textColor: tuple = (200, 200, 200), borderColor: tuple = (200, 200, 200), temporary = False, angle = 0, stretch = 1, middle = False, priority: float = 2, gen: bool = True):
            self.borderSize = borderSize
            self.middle = middle
            self.text = text
            self.width = width
            self.height = height
            if size is None:
                size = round(self.height)
            self.size = size
            self.textSurface = RenderText(surface = surface, enabled = True, x = x+self.borderSize-size/10*self.middle, y = y+self.borderSize-size/15*self.middle, xOffset = xOffset, yOffset = yOffset, text = self.text, font = font, size = size, color = textColor, temporary = temporary, angle = angle, stretch = stretch, middle = middle, priority = priority, gen = False)
            self.font = font
            self.textColor = textColor
            self.color = color
            self.activeColor = activeColor
            self.borderColor = borderColor
            
            
            
            if imageName is not None:
                self.renderSurface = imageName
            else:
                if drawType == "rect":
                    self.renderSurface = pygame.Surface((self.width, self.height))
                    self.renderSurface.fill(self.borderColor)
                    innerRect = pygame.Rect(self.borderSize, self.borderSize, self.width - self.borderSize * 2, self.height - self.borderSize * 2)
                    pygame.draw.rect(self.renderSurface, self.color, innerRect)
                elif drawType == "circ":
                    self.renderSurface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                    pygame.draw.circle(self.renderSurface, self.borderColor, (self.height/2, self.height/2), min(self.height/2, self.height/2))
                    pygame.draw.circle(self.renderSurface, self.color, (self.height/2, self.height/2), min(self.height/2, self.height/2) - self.borderSize)
            
            if hoverImageName is not None:
                self.activeSurface = hoverImageName
            elif activeColor is not None:
                if drawType == "rect":
                    self.activeSurface = pygame.Surface((self.width, self.height))
                    self.activeSurface.fill(self.borderColor)
                    pygame.draw.rect(self.activeSurface, self.activeColor, innerRect)
                elif drawType == "circ":
                    self.activeSurface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                    pygame.draw.circle(self.activeSurface, self.borderColor, (self.height/2, self.height/2), min(self.height/2, self.height/2))
                    pygame.draw.circle(self.activeSurface, self.activeColor, (self.height/2, self.height/2), min(self.height/2, self.height/2) - self.borderSize)
            else:
                self.activeSurface = False
            
            super().__init__(imageName = self.renderSurface, strName = strName, clickAction = clickAction, hoverAction = hoverAction, unHoverAction = unHoverAction, arguments = arguments, hoverArguments = hoverArguments, unHoverArguments = unHoverArguments, surface = surface, temporary = temporary, enabled = enabled, hoverImageName = self.activeSurface, x = x, xOffset = xOffset, y = y, yOffset = yOffset, width = width, height = height, middle = middle, priority = priority, angle = angle, stretch = stretch, gen = gen)
            
            if type(self) is RenderTextButton and gen:
                renders.append(self)

        def draw(self):
            super().draw()
            self.textSurface.draw()
        
    class RenderInput(RenderObject):
        def __init__(self, surface: pygame.surface = screen, enabled = True, x: int = 0, y: int = 0, xOffset: int = 0, yOffset: int = 0, text: str = "example", font: pygame.font = defaultFont, size: int = 30, borderSize = 5, color: tuple = (0, 0, 0), activeColor = (100, 100, 100), textColor: tuple = (200, 200, 200), borderColor: tuple = (200, 200, 200), temporary = False, angle = 0, stretch = 1, middle = False, priority: float = 2, gen: bool = True):
            self.borderSize = borderSize
            self.middle = middle
            self.text = text
            self.textSurface = RenderText(surface = surface, enabled = True, x = x+self.borderSize-size/10*self.middle, y = y+self.borderSize-size/15*self.middle, xOffset = xOffset, yOffset = yOffset, text = self.text, font = font, size = size, color = textColor, temporary = temporary, angle = angle, stretch = stretch, middle = middle, priority = priority, gen = False)
            self.height = self.textSurface.height + self.borderSize * 2
            self.width = self.textSurface.width + self.borderSize * 2
            self.size = size
            self.font = font
            self.mainColor = color
            self.activeColor = activeColor
            self.color = self.mainColor
            self.textColor = textColor
            self.borderColor = borderColor
            self.renderSurface = pygame.Surface((self.width, self.height))
            self.renderSurface.fill(self.borderColor)
            innerRect = pygame.Rect(self.borderSize, self.borderSize, self.width - self.borderSize * 2, self.height - self.borderSize * 2)
            pygame.draw.rect(self.renderSurface, self.color, innerRect)
            super().__init__(surface = surface, temporary = temporary, enabled = enabled, x = x, y = y, width = self.width, height = self.height, priority = priority, angle = angle, stretch = stretch)

            self.active = False
            self.hovered = False
            
            if type(self) is RenderInput and gen:
                    renders.append(self)
            
        def setOn(self, on: bool):
            global activeInput
            if on:
                activeInput = self
                self.color = self.activeColor
            else:
                if activeInput == self:
                    activeInput = None
                self.color = self.mainColor
            self.update()
            
        def update(self):
            self.textSurface = RenderText(surface = self.surface, enabled = True, x = self.x+self.borderSize-self.size/10*self.middle, y = self.y+self.borderSize-self.size/15*self.middle, xOffset = self.xOffset, yOffset = self.yOffset, text = self.text, font = self.font, size = self.size, color = self.textColor, temporary = self.temporary, angle = self.angle, stretch = self.stretch, middle = self.middle, priority = self.priority, gen = False)
            self.height = self.textSurface.height + self.borderSize * 2
            self.width = self.textSurface.width + self.borderSize * 2
            self.renderSurface = pygame.Surface((self.width, self.height))
            self.renderSurface.fill(self.borderColor)
            innerRect = pygame.Rect(self.borderSize, self.borderSize, self.width - self.borderSize * 2, self.height - self.borderSize * 2)
            pygame.draw.rect(self.renderSurface, self.color, innerRect)
        
        def click(self, me):
            if me:
                self.active = True
            else:
                self.active = False
                self.setOn(False)
        
        def hover(self, hover = False):
            if hover:
                self.hovered = True
                self.setOn(True)
            elif self.hovered:
                self.hovered = False
                if not self.active:
                    self.setOn(False)
        
        def draw(self):
            drawRotated(surface = self.surface, img = self.renderSurface, x = self.x + self.xOffset, y = self.y + self.yOffset, angle = self.angle, width = self.width * self.sizeMulti, height = self.height * self.sizeMulti, stretch = self.stretch, middle = self.middle)
            self.textSurface.draw()
        


    class GameObject():
        def __init__(self, strName = "image", x = 0, y = 0, renderObject = None, enabled = True, angle = 0, priority = 2):
            global renders
            self.strName = strName
            self.x = x
            self.y = y
            self.angle = angle
            self.enabled = enabled
            self.priority = priority
            renderObject.x = self.x
            renderObject.y = self.y
            renderObject.angle = self.angle
            renderObject.strName = self.strName
            renderObject.priority = self.priority
            renderObject.enabled = self.enabled
            self.renderObject = renderObject
            
        def update(self):
            self.renderObject.x = self.x
            self.renderObject.y = self.y
            self.renderObject.angle = self.angle
            self.renderObject.enabled = self.enabled
            self.renderObject.priority = self.priority

    
    
def example():    
    init()
    images = ("image", "image2", "image2")
    animation = RenderAnimation(imageNames = images, slowdown = 10, rotation = 1, height = 200, width = 200, x = middle[0], y = middle[1])

    while running:
        draw()
    
    
if __name__ == "__main__":
    example()