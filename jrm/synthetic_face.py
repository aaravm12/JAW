"""Original procedural cartoon face for positive ML replay tests (CC0-1.0).
Not a person, not a human recording, and not evidence of human tracking accuracy.
"""
import math
import cv2
import numpy as np


def cartoon_frame(t, moving=False):
    opening = (1-math.cos(2*math.pi*.25*t))/2 if moving else 0.
    image = np.full((640,480,3),200,np.uint8)
    cv2.ellipse(image,(240,320),(150,220),0,0,360,(155,195,223),-1)
    for x in (180,300):
        cv2.ellipse(image,(x,250),(32,15),0,0,360,(250,250,250),-1)
        cv2.circle(image,(x,250),12,(70,75,65),-1)
        cv2.circle(image,(x,250),6,(10,10,10),-1)
        cv2.ellipse(image,(x,229),(38,12),180,0,180,(65,55,50),4)
    cv2.line(image,(240,265),(218,350),(110,145,180),3)
    cv2.ellipse(image,(240,354),(23,10),0,0,180,(110,135,170),2)
    half_height=15+int(round(28*opening))
    cy=408+int(round(10*opening))
    cv2.ellipse(image,(240,cy),(55,half_height),0,0,360,(75,70,125),-1)
    cv2.ellipse(image,(240,cy),(46,max(5,half_height-9)),0,0,360,(30,25,35),-1)
    if opening < .12:
        cv2.ellipse(image,(240,cy-2),(46,5),0,0,360,(230,230,230),-1)
    else:
        cv2.ellipse(image,(240,cy-half_height+12),(35,4),0,0,360,(230,230,230),-1)
    return image
