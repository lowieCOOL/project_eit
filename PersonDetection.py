""" IMPORTS """

import numpy as np
import cv2


""" MAIN """

if __name__ == '__main__':

    webcam = True

    # open webcam video stream
    if webcam:
        cap = cv2.VideoCapture(0)
        
    else:
        import pyrealsense2 as rs
        
        # Configure streams
        pipeline = rs.pipeline()
        config = rs.config()

        config.enable_stream(rs.stream.depth, rs.format.z16, 30)
        other_stream, other_format = rs.stream.color, rs.format.bgr8
        config.enable_stream(other_stream, other_format, 30)

        # Start streaming
        pipeline.start(config)
        profile = pipeline.get_active_profile()


    # initialize the HOG descriptor/person detector
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    cv2.startWindowThread()

    # the output will be written to output.avi
    out = cv2.VideoWriter(
        'output.avi',
        cv2.VideoWriter_fourcc(*'MJPG'),
        15.,
        (640,480))

    try:
        while(True):
            if webcam:
                # Capture frame-by-frame for computer webcam
                ret, frame = cap.read()
            
            else:
                frames = pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                color_image = np.asanyarray(color_frame.get_data())
                    
            
                # resizing for faster detection
                frame = cv2.resize(color_image, (640, 480))
            
            # using a greyscale picture, also for faster detection
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
            # detect people in the image
            # returns the bounding boxes for the detected objects
            boxes, weights = hog.detectMultiScale(gray, winStride=(8,8) )
        
            boxes = np.array([[x, y, x + w, y + h] for (x, y, w, h) in boxes])
        
            for (xA, yA, xB, yB) in boxes:
                # display the detected boxes in the colour picture
                cv2.rectangle(frame, (xA, yA), (xB, yB),
                                  (0, 255, 0), 2)
            
            # Write the output video
            out.write(frame.astype('uint8'))
            # Display the resulting frame
            cv2.imshow('frame',frame)
            
            # Escape
            k = cv2.waitKey(1)
            if k == 27:
                break
            
    finally:
        if webcam:
            # When everything done, release the capture
            cap.release()
        else:
            pipeline.stop()
        # release the output
        out.release()
        # finally, close the window
        cv2.destroyAllWindows()