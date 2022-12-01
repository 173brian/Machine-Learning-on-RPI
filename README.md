# RPIML
This is a machine learning program intended to be executed on a Raspberry Pi. This program controls an aperture to look for inputs, and then saves those inputs into a machine learning document, which it then uses to make decisions about how to reach those inputs more quickly in the future.

## How it Works
This program utilizes binary searches for quick lookups in data sets to make decisions about where the most probable place it will receive an input is. The further a lookup is from where the aperture currently is the less likely the program is to look for it. This enables the program to learn how to find the quickest route to its goal of receiving input.

## Setup
The hardest part of the setup for this program is wiring the physical components used in this project. The image below shows the pinout associated with most Raspberry Pi boards. The image depicts a Pi4, but the board I used was a Pi3 B+, and also worked fine. The pins I used can be switched with any pins labelled GPIO, but the default pin I used for receiving input was 33, a 5v pin at 4 which is set by default, and a ground pin at 6 which is set by default. I also initialized 37 as the output pin for controlling the servo, and 35 for another 5v pin if it's needed.
<img src="Images/GPIO.png">

## Files
The successful lookups are handled by the Raspberry Pi and stored in the following file format
```
rpi.ml (folder) contains files used in machine learning
+--machinelearning.dat (file) the file that stores past successful lookups
```

## Video Walkthrough of Project
https://youtu.be/TYgS0UsCdVQ