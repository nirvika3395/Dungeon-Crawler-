#character.py 

import pygame 
import constrants
import math 
from constrants import BLUE

class Character():

    def __init__(self,x,y,image):
        self.image = image 
        self.flip = False
        self.rect = pygame.Rect(0,0,40,40)
        self.rect.center =(x,y)
    
    def move(self,deltaX,deltaY):
        if deltaX<0:
            self.flip = False
        elif deltaX > 0:
            self.flip = True 

        #diagonal movements speed 
        if deltaX != 0 and deltaY !=0:
            deltaX *= (math.sqrt(2)/2)
            deltaY *= (math.sqrt(2)/2)

        self.rect.x += deltaX
        self.rect.y += deltaY


    def draw(self,screen):
        flipped_image= pygame.transform.flip(self.image,self.flip,False)
        screen.blit(flipped_image,self.rect)
       # screen.blit(self.image, self.rect)
        pygame.draw.rect(screen,BLUE,self.rect,1)


