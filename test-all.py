#!/usr/bin/python

#
#  Copyright (C) 2015-2016 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import sys
import socket
import xml.etree.ElementTree as ET

from dispose_log import Color_Print
mondelloStr = "mondello"
MIPI = "mipi"
NONMIPI = "non-mipi"
inputCams = {}

# environment values for os
environCamInput = "cameraInput"
environCamInput2 = "cameraInput2"
environCamMipiCapture = "cameraMipiCapture"
environCamPixter2Addr = "cameraPixter2Addr"

# dual related variables
dualCamDescriptor = "dual case for "
secondCamPostFix = "-2"

profileList=["./libcamhal_profile.xml", "/etc/camera/libcamhal_profile.xml"]
debugProfileList=["./libcamhal_profile_debug.xml", "/etc/camera/libcamhal_profile_debug.xml"]

t_filename=[]

def getInputFromXML(xml=None):
    tree = ET.parse(xml)
    root = tree.getroot()
    for child in root:
        if child.tag == "Sensor":
            camName = child.attrib["name"]
            if MIPI in child.attrib["description"]:
                inputCams[camName]=[MIPI]
            else:
                inputCams[camName]=[NONMIPI]

            if secondCamPostFix in camName:
                mainCamName = camName.replace(secondCamPostFix, "")
                inputCams[dualCamDescriptor + mainCamName] = [MIPI + ", main:" + mainCamName + ", second:" + camName]

def getAllCamInput():
    for xml in profileList:
        if os.path.exists(xml):
            getInputFromXML(xml)
            break;

    for xml in debugProfileList:
        if os.path.exists(xml):
            getInputFromXML(xml)
            break;

def selectCamInput():
    global xrcHost
    print "available camera input:"
    inputCamsName = inputCams.keys()
    for item in inputCamsName:
        comment = ""
        for support in inputCams[item]:
            comment = comment + " " + support
        print "  " + str(inputCamsName.index(item)) + ": " + item + " (" + comment + " )"

    paraNum = len(sys.argv)
    if  paraNum <= 1:
        cameraInput = int(raw_input("please select one:"))
    elif (paraNum >= 2) and (paraNum <= 3):
        cameraInput = int(sys.argv[1])
    else:
        print "Error: Invalid parameters,please input no more than 2 parameters"
        exit(1)

    testDualCam = False
    os.environ[environCamInput]="tpg"
    os.environ[environCamInput2]=""
    if cameraInput <= len(inputCamsName):
        if dualCamDescriptor in inputCamsName[cameraInput]:
            mainCamName = inputCamsName[cameraInput].replace(dualCamDescriptor, "")
            secondCamName = mainCamName + secondCamPostFix
            os.environ[environCamInput] = mainCamName
            os.environ[environCamInput2] = secondCamName
            os.environ[environCamMipiCapture] = "true"
            testDualCam = True
        else:
            os.environ[environCamInput] = inputCamsName[cameraInput]

    if testDualCam == False and 0 == cmp(os.environ[environCamInput][0:len(mondelloStr)], mondelloStr):
        print "please specify XRC host IP for automatic data feeding, like 10.238.224.190"
        if paraNum == 3:
            xrcHost = sys.argv[2]
        else:
            xrcHost = raw_input("please input:")

        if xrcHost == "":
            print "Error: XRC host IP must be specified for mondello automatic test!"
            exit(1)
        else:
            print "XRC host is " + xrcHost

def printCamVariables():
    print environCamMipiCapture + " = " + os.getenv(environCamMipiCapture)
    print environCamInput + " = " + os.getenv(environCamInput)
    print environCamInput2 + " = " + os.getenv(environCamInput2)

def runCamTest(filename=None):
    global t_filename

    t_filename.append(filename)
    if os.environ[environCamInput] == mondelloStr:
        os.system('./run_all_mondello_tests.sh' + xrcHost)
    else:
        os.system('./libcamhal_test 2>&1 | tee %s' % filename)
    print "=============================================================================="

def supportMipiCapture(inputName):
    if MIPI in inputCams[inputName]:
        return True
    return False

def supportNonMipiCapture(inputName):
    if NONMIPI in inputCams[inputName]:
        return True
    return False

def summary_and_compare(summarize=False, compare=False, jsonfile=None):
    def execute(cmd):
        retcode = os.system(cmd)
        if retcode != 0:
            s = "Result: failure."
            Color_Print.red(s)
        else:
            pass

    if t_filename:
        if summarize:
            for i in t_filename:
                cmd = './dispose_log.py summary -f %s' % i
                execute(cmd)
        elif compare:
            if not jsonfile:
                jsonfile = "camera_compare.json"
            for i in t_filename:
                cmd = './dispose_log.py compare -f %s -j %s' % (i, jsonfile)
                execute(cmd)
        else:
            s = "Error: please figure out action as 'summarize' or 'compare'."
            Color_Print.red(s)
            exit(1)
    else:
        s = "No testing result log to summarize or compare."
        Color_Print.red(s)

def sendDataViaSocket(hostIp, hostPort, fmt, resolution, lanesNum, interlaced, channel):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostIp, hostPort))
    s.sendall("stop fmt=%s size=%s lanes=%d interlaced=%d ch=%d fps=30 start" % (fmt, resolution, lanesNum, interlaced, channel))
    s.close()

def validIp(addr):
    try:
        socket.inet_aton(addr)
        return True
    except:
        return False


xrcHost = ""

getAllCamInput()

selectCamInput()

inputName = os.environ[environCamInput]
input2Name = os.environ[environCamInput2]

if secondCamPostFix in input2Name:
    print "test the dual camera case:"
    printCamVariables()
    ip = os.getenv(environCamPixter2Addr)
    if validIp(ip):
        print "the pixter2 ip address is: %s" % ip
    else:
        ip = raw_input("please enter the pixter2 ip address:")
    port1 = 12345
    port2 = 12346
    if 0 == cmp("mondello-mipi", inputName):
        cases = [
            #[case name, format, resolution, lanes number, interlaced],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_1080p_UYVY", "UYVY", "1920x1080", 4, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_720p_UYVY", "UYVY", "1280x720", 4, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_vga_UYVY", "UYVY", "640x480", 2, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_720x576_UYVY", "UYVY", "720x576", 2, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_interlaced_1080i_UYVY", "UYVY", "1920x1080", 4, 1],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_interlaced_576i_UYVY", "UYVY", "720x576", 2, 1],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_interlaced_480i_UYVY", "UYVY", "720x480", 2, 1],

            ["camHalDualTest.dual_mondello_qbuf_dqbuf_1080p_YUYV", "YUYV", "1920x1080", 4, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_720p_YUYV", "YUYV", "1280x720", 4, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_vga_YUYV", "YUYV", "640x480", 2, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_720x576_YUYV", "YUYV", "720x576", 2, 0],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_interlaced_1080i_YUYV", "YUYV", "1920x1080", 4, 1],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_interlaced_576i_YUYV", "YUYV", "720x576", 2, 1],
            ["camHalDualTest.dual_mondello_qbuf_dqbuf_interlaced_480i_YUYV", "YUYV", "720x480", 2, 1],

            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_1080p_BG24", "RGB888", "1920x1080", 4, 0],
            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_720p_BG24", "RGB888", "1280x720", 4, 0],
            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_vga_BG24", "RGB888", "640x480", 2, 0],
            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_720x576_BG24", "RGB888", "720x576", 2, 0],
            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_interlaced_1080i_BG24", "RGB888", "1920x1080", 4, 1],
            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_interlaced_576i_BG24", "RGB888", "720x576", 2, 1],
            ["camHalDualTest.dual_mondello_rgb888_qbuf_dqbuf_interlaced_480i_BG24", "RGB888", "720x480", 2, 1],

            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_1080p_RGB565", "RGB565", "1920x1080", 4, 0],
            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_720p_RGB565", "RGB565", "1280x720", 4, 0],
            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_vga_RGB565", "RGB565", "640x480", 2, 0],
            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_720x576_RGB565", "RGB565", "720x576", 2, 0],
            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_interlaced_1080i_RGB565", "RGB565", "1920x1080", 4, 1],
            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_interlaced_576i_RGB565", "RGB565", "720x576", 2, 1],
            ["camHalDualTest.dual_mondello_rgb565_qbuf_dqbuf_interlaced_480i_RGB565", "RGB565", "720x480", 2, 1],
        ]
        for case in cases:
            sendDataViaSocket(ip, port1, case[1], case[2], case[3], case[4], 0)
            sendDataViaSocket(ip, port2, case[1], case[2], case[3], case[4], 1)
            os.system('./libcamhal_test --gtest_filter=%s' % case[0])
    print "=============================================================================="
else:
    # ISA is not supported for MIPI pipeline
    if supportMipiCapture(inputName):
        print "To test when the BE capture is disabled and MIPI is enabled:"
        filename = inputName + "_mipi.log"
        os.environ[environCamMipiCapture] = "true"
    if supportNonMipiCapture(inputName):
        print "To test when the BE capture is enabled and MIPI is disabled:"
        filename = inputName + "_non-mipi.log"
        os.environ[environCamMipiCapture] = "false"

    printCamVariables()
    runCamTest(filename)

# Summarize and compare
summary_and_compare(compare=True)
summary_and_compare(summarize=True)

