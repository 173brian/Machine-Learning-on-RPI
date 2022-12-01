import sys

import RPi.GPIO as GPIO
import random
import os
import time
from time import sleep

class RPIML:
    # Machine learning variables:
    mlfolderlocation = "rpi.ml"
    mlfile = "machinelearning.dat"
    # Variables to keep track of GPIO settings for the Raspberry Pi
    inputpin = None
    outputnegative = None
    outputdata = None
    # Variables to keep track of the motor config and status
    lasttimefound = None
    ground = None
    motor = None
    previousweight = None
    weight = None
    duty = None

    def __init__(self):
        # Setting up Pi GPIO info
        self.inputpin = 33
        self.outputnegative = 35
        self.outputdata = 37
        self.ground = 6
        # Setting up motor info
        self.lasttimefound = time.time()
        self.previousweight = 0
        self.weight = 0
        self.duty = 2
        # Setting up the Raspberry Pi board
        GPIO.setmode(GPIO.BOARD)
        # Initialize machine learning files
        self.CheckDir()
        self.CheckMLFile()
        # Set up the GPIO pins listed above
        self.SetPinout()
        # Set up the motor
        self.MotorInit()
        # Run the main loop
        self.MLMain()


    def CheckDir(self): # Checks to make sure that the folder structure needed for machine learning exists
        if (os.path.isdir(self.mlfolderlocation)):
            print("mlfolder exists.")
        else:
            os.mkdir(self.mlfolderlocation)
            print ("mlfolder created successfully.")

    def CheckMLFile(self): # Checks to make sure that the file used for machine learning is present
        if (os.path.exists(os.path.join(self.mlfolderlocation, self.mlfile))):
            print("mlfile exists.")
        else: # file doesn't exist, create it:
            open(os.path.join(self.mlfolderlocation, self.mlfile), "x") # Create file
            with open(os.path.join(self.mlfolderlocation, self.mlfile), "w") as file: # Setup file
                file.write("[RPI_Lookups]:0")
            print("mlfile created successfully.")

    def SetPinout(self): # Calls Raspberry Pi pinout assignment functions to allow this program to interact with the board
        GPIO.setup(self.inputpin, GPIO.IN)
        GPIO.setup(self.outputnegative, GPIO.OUT)
        GPIO.setup(self.outputdata, GPIO.OUT)
        # Pin 39 is already a ground pin, so it requires no setup.
        GPIO.output(self.outputnegative, True)
        GPIO.output(self.outputdata, True)
        print("Pinout completed.")

    def MotorInit(self): # Sets up the motor in accordance with servo standards
        self.motor = GPIO.PWM(self.outputdata, 50) # GPIO 11 for PWM with 50Hz
        self.motor.start(2.5) # Initialization

    def MLMain(self): # The main entry point for controlling the flow of the program
        continuetraining = True
        while(continuetraining):
            trainingintervals = 50 # How many trials will be run before prompting the user to stop or continue
            for i in range(trainingintervals):
                print(f"Test {i}/{trainingintervals}")
                self.MoveMotor() # Seek input trainingintervals number of times
            inputbool = True
            while(inputbool): # Prompts the user to continue or quit. Prevents bad input.
                print(f"Would you like to continue for another {trainingintervals} intervals? (Y/n): ", end="")
                userinput = input()
                if (userinput.lower().__contains__("y")):
                    inputbool=False
                elif (userinput.lower().__contains__("n")):
                    inputbool=False
                    continuetraining=False


    def MoveMotor(self):
        readvoltagedelay = 100 # Number of continuous reads that must be completed before a position will be considered 'on'
        self.previousweight = self.weight
        self.weight = self.GetDutyCycle(self.previousweight) # Asks the AI to make a 'weighted' decision as to where the best chance of finding the next input is.
        dutyInterval = .1
        print(f"Duty received: {self.weight}")
        if (self.previousweight == 0): # Check to make sure that duty won't start at a value that can't be used
            self.previousweight = 2
        self.duty = self.previousweight # Duty starting place is previousweight
        if (self.previousweight >= self.weight): # Handles whether the aperture is sweeping left to right (positive) or right to left (negative)
            dutyInterval = -1 * abs(dutyInterval)
        else:
            dutyInterval = abs(dutyInterval)
        for t in range(int(abs((self.duty-self.weight)/dutyInterval))): # repeats the number of times needed to cover the range between where the aperature is and where it needs to go:
            print(f"Current duty: {self.duty}")
            if (time.time() - self.lasttimefound > 1): # Only check if an input is received if at least 1 second has passed since last recording to prevent double input
                triggerval = GPIO.input(self.inputpin)
                if (triggerval): # A found signal was received:
                    print("Input received.")
                    goodinput = True
                    for i in range(readvoltagedelay): # Require multiple, sustained readings in a row to prevent electrical interference from being accidentally recorded.
                        print("Input")
                        if not (GPIO.input(self.inputpin)): # If input isn't present:
                            goodinput = False # Break the loop checking for input
                            print("Bad input caught.")
                            break
                        i += 1
                    if (goodinput): # If input was sustained
                        self.AddValueToMLDoc(self.duty) # Add value to machinelearning file
                        self.lasttimefound = time.time() # Set lasttimefound to now
                        break
            self.duty += dutyInterval # Move the aperture by dutyinterval amount
            self.motor.ChangeDutyCycle(self.duty) # Sets the aperture to the new position
            sleep(.1) # Stop the program to allow the motor to catch up.

    def GetDutyCycle(self, previousweight=0): # The AI part of this program
        with open(os.path.join(self.mlfolderlocation, self.mlfile), 'r') as file:
            contents = file.readlines() # Read machine learning file
        contents.remove(contents[0])
        for line in contents:
            contents[contents.index(line)] = line.strip() # Make sure data is in a format useful to the program
        greatestdict = {"greatestval" : 0, "greatestvaladdress" : 0}
        address = 0
        print(f"contents:{contents}")
        for line in contents: # For every line in the machine learning file (guaranteed to be relatively small so o(n) runtime shouldn't impact runtime greatly.
            if abs((float(line.split(':')[0]) - previousweight ) > 1): # If duty spot is at least one away to minimize the impact of inaccuracies in reading
                if (int(line.split(':')[1]) > greatestdict.get("greatestval")): # If the spot read has more occurences than the previous reads
                    greatestdict["greatestval"] = int(line.split(':')[1])
                    greatestdict["greatestvaladdress"] = address
            address += 1
        print(f"greatestdict: {greatestdict}")
        if (previousweight == 0): # Check to make sure previousweight can be used even when it's just been initialized
            previousweight= 1
        previousweight = int(previousweight) # Make previousweight an integer for our random value generator to work with
        zerobased = previousweight - 2 # Duty cycles go from 2-12, to make math easier and use the values 0-10 we briefly compensate by subtracting 2
        newbottom = ((zerobased + 1 ) % 11) + 2 # The new bottom is one ahead of where it was before.
        newweight =  random.randint(newbottom, 12) # Newweight is a random number between the newbottom and top of the duty cycle (12)
        if (greatestdict["greatestval"] != 0): # If a machine learning value was found
            if abs(greatestdict["greatestval"] - newweight) < abs(newweight - previousweight): # If the 'smart decision' is more likely to occur than the newweight is close.
                if abs(newweight - previousweight) > 3: # If we're doing a significant reset or moving forward (a move that covers more than 45 degrees)
                    self.lasttimefound = time.time() # Reset the find timer to prevent bad input when resetting the aperture.
                return newweight
            else: # The AI choice is smarter:
                return float(contents[greatestdict["greatestvaladdress"]].split(':')[0])
        else: # Make a random decision to learn more
            if abs(newweight - previousweight) > 3:
                self.lasttimefound = time.time()
            return newweight


    def AddValueToMLDoc(self, weight): # Save the position where an input was received to the data set for this program.
        with open(os.path.join(self.mlfolderlocation, self.mlfile), 'r') as file:
            contents = file.readlines() # Get info from file
        for item in contents:
            contents[contents.index(item)] = item.strip() # Format file info
        print("Contents before performing function: ", contents) # Print file info
        location = self.BstIndex(contents, weight) # Lookup weight in info
        found = list(location.values())[0]
        position = list(location.values())[1]
        if (found): # If item was found:
            contents[position] = f"{contents[position].split(':')[0]}:{int(contents[position].split(':')[1]) + 1}"
        else: # Item wasn't found:
            if (position == len(contents)): # If location is at the end of the list:
                contents.append(f"{weight}:1") # Append rather than insert to avoid errors.
            else: # Item wasn't found at the end of the list
                contents.insert(position, f"{weight}:1") # Insert in middle
        contents[0] = f"{contents[0].split(':')[0]}:{int(contents[0].split(':')[1]) + 1}" # Update header information
        print("Contents after performing function: ", contents)
        newfilecontents = "\n".join(contents)
        print(newfilecontents)
        with open(os.path.join(self.mlfolderlocation, self.mlfile), 'w') as file:
            file.write(newfilecontents) # Save new file contents.

    """
    BstIndex controls the BstInternal method, calls the recursive method with the values determined here in the BstIndex. Efficiency is available below.
    """
    def BstIndex(self, array, val): # Modified BST to require as few lookups as possible for this program. Because this isn't a true bst with nodes there has to be an end condition where the computer searches through the remaining items, else an endless loop can occur. As the dataset approaches infinity the limit of lookups approaches log(n) + 10 + 1000/n. BST won't start dividing values until the dataset is larger than 37.016.
        return self.BstInternal(array, val, 1, len(array), round(1000/len(array))) # Returns the dictionary output of BstInternal.

    """
    BstInternal aims to cut the document down to a size that provides as few readings as necessary without entering an infinite loop looking for items that don't exist. Takes a target size to cut the document down to, and then reads through the remaining values until the val or a larger val is found, whichever happens first.
    """
    def BstInternal(self, array, val, bottom, top, endCondition): # Efficiency is more complex than the overview given in BstIndex, some repeat values are allowed which means that the number of calls could exceed what were listed above by a factor of three (for each signature type), but this would be rare.
        pos = int((top+bottom)/2) # Position is located at the middle of the document
        if (abs(top - bottom) <= endCondition): # If remaining document size is less than or equal to the endcondition value:
            pos = bottom # Position is at the document's currently defined bottom
            dict = {"Found": False}  # Return dictionary for found values
            for i in range(len(array)-bottom): # For currently defined bottom to top.
                pos = bottom + i # Current position is bottom + loop iteration
                if (abs(float(array[pos].split(':')[0]) - val) < .1): # Value is in document:
                    dict["Found"] = True # Update dictionary value for Found.
                    break # End search.
                elif val < float(array[pos].split(":")[0]): # Value is now less than read value:
                    pos -= 1
                    break # End search.
            dict["Position"] = pos # Position information where spot was found or passed.
            if (dict["Found"] == False):
                dict["Position"] += 1
            return dict # returns the INDEX of the value and whether spot was found.
        if float(array[pos].split(':')[0]) == (val): # Item was found during Bst splits
            dict = {"Found": True, "Position": pos}  # Return dictionary for found values
            return dict # returns the INDEX of the value and whether spot was found.
        elif float(array[pos].split(':')[0]) > val: # Document value is larger than currently read value:
            return self.BstInternal(array, val, bottom, pos - 1, endCondition) # Read everything above (lower than) the current value
        else: # Document value is less than currently read value:
            return self.BstInternal(array, val, pos + 1, top, endCondition) # Read everything below (higher than) the current value

rpiml = RPIML()
