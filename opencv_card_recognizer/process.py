import cv2
import numpy as np
import os
from pathlib import Path
from opencv_card_recognizer import augtest
from opencv_card_recognizer import augment

def findContours(img, original, draw=False):
    contours, hier = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    four_corners_set = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        perimeter = cv2.arcLength(cnt, closed=True)

        maxArea = 0

        if area > 2000:
            approx = cv2.approxPolyDP(cnt, 0.01*perimeter, closed=True)

            numCorners = len(approx)

            if draw and numCorners == 4:
                # cv2.drawContours(original, cnt, -1, (255, 0, 0), 3)

                # create bounding box around shape
                x, y, w, h = cv2.boundingRect(approx)
                cv2.rectangle(original, (x, y), (x+w, y+h), (0, 255, 0), 2)

                # make sure the image is oriented right top left, bot left, bot right, top right
                l1 = np.array(approx[0]).tolist()
                l2 = np.array(approx[1]).tolist()
                l3 = np.array(approx[2]).tolist()
                l4 = np.array(approx[3]).tolist()

                # find which ones have similar x values
                similarX = []
                sortedX = sorted([l1,l2,l3,l4], key=lambda x: x[0][0])
                # sortedX[0] and sortedX[1] are the left half
                # the one with the smaller y value goes first

                finalOrder = []
                finalOrder.extend(sorted(sortedX[0:2], key=lambda x: x[0][1]))

                # now sortedX[1] and sortedX[2] are the right half
                # the one with the larger y value goes first
                finalOrder.extend(sorted(sortedX[2:4], key=lambda x: x[0][1], reverse=True))
                # print(approx)
                # print(finalOrder)

                # if area > maxArea:
                #     maxArea = area
                #     four_corners_set = []

                four_corners_set.append(finalOrder)
                for a in approx:
                    cv2.circle(original, (a[0][0], a[0][1]), 10, (255, 0, 0), 3)
                    # print((a[0][0], a[0][1]))
                # print("___________")

    return four_corners_set

def flatten_card(img, set_of_corners):
    width, height= 200, 300
    img_outputs = []

    for corner_set in set_of_corners:
        # define 4 corners of the King of Spades card
        pts1 = np.float32(corner_set)
        # now define which corner we are referring to
        pts2 = np.float32([[0,0],[0,height],[width,height],[width,0]])

        # transformation matrix
        matrix = cv2.getPerspectiveTransform(pts1, pts2)

        imgOutput = cv2.warpPerspective(img, matrix, (width, height))
        img_outputs.append(imgOutput)

    return img_outputs

# def empty(x):
#     pass
#
# cv2.namedWindow("Parameters2")
# cv2.resizeWindow("Parameters2",640,240)
# cv2.createTrackbar("Threshold1","Parameters2",40,255,empty)
# cv2.createTrackbar("Threshold2","Parameters2",24,255,empty)
# originally 51 72
# then 35 60

def get_corner_snip(flattened_images):
    c = 0
    cropped_images = []
    for img in flattened_images:
        # img have shape (300, 200)
        # crop the image in half first, and then the width in half again
        crop = img[10:120, 0:35]

        # resize by a factor of 4
        crop = cv2.resize(crop, None, fx=4, fy=4)

        # threshold the corner
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        # blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # threshold1 = cv2.getTrackbarPos("Threshold1", "Parameters2")
        # threshold2 = cv2.getTrackbarPos("Threshold2", "Parameters2")

        gray=cv2.bilateralFilter(gray,11,17,17)
        canny = cv2.Canny(gray, 40, 24)
        kernel = np.ones((3, 3))
        result = cv2.dilate(canny, kernel=kernel, iterations=2)


        # gray=cv2.bilateralFilter(gray,11,17,17)
        # edge=cv2.Canny(gray,30,200)
        # result = edge

        # result = gray

        # result = cv2.erode(dial, kernel=kernel, iterations=1)

        # cv2.imshow('Image' + str(c) + '-before-warp.png', result)
        cv2.imwrite('Image' + str(c) + '-before-warp.png', img)
        cv2.imwrite('Image' + str(c) + '.png', result)
        c += 1

        cropped_images.append([result, gray])

    return cropped_images

def split_rank_and_suit(cropped_images):
    imgC = 0
    rank_suit_mapping = []
    for img, original in cropped_images:
        # print(img.shape)

        # find the two largest contours
        contours, hier = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        highest_two = dict()
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 1500:
                cv2.fillPoly(img, pts=[cnt], color=0)
                continue
            perimeter = cv2.arcLength(cnt, closed=True)
            highest_two[area] = [cnt, perimeter]

        # select the largest two in this image
        cntC = 0
        mapping = []
        # if len(list(highest_two.keys())) != 2:
        #     return []
        # print(highest_two.keys())
        for area in sorted(highest_two)[0:2]:
            cnt = highest_two[area][0]
            perimeter = highest_two[area][1]
            approx = cv2.approxPolyDP(cnt, 0.02*perimeter, closed=True)
            x, y, w, h = cv2.boundingRect(approx)
            # cv2.rectangle(img, (0, y), (img.shape[0], y+h), (255, 0, 0), 2)
            crop = original[y:y+h][:]
            cv2.imwrite('{}-{}-before.png'.format(imgC, cntC), crop)

            sharpened = augment.contrast(crop, 30)
            cv2.imwrite('{}-{}-sharp.png'.format(imgC, cntC), sharpened)

            # sharpened[sharpened < 175] -= 150
            # sharpened[sharpened < 0] = 0

            for i in range(sharpened.shape[0]):
                for j in range(sharpened.shape[1]):
                    if sharpened[i,j] < 150:
                        sharpened[i,j] = max(0, sharpened[i,j] - 60)
                    if sharpened[i,j] > 150:
                        sharpened[i,j] = 255



            cv2.imwrite('{}-{}-sharp-after-filter.png'.format(imgC, cntC), sharpened)

            # cv2.imwrite('{}-{}-crop.png'.format(imgC, cntC), crop)
            # cv2.imwrite('{}-{}-sharp.png'.format(imgC, cntC), sharpened)

            cntC += 1
            mapping.append([sharpened, y])

        imgC += 1

        # # lets store rank and then suit
        mapping.sort(key=lambda x: x[1])
        # print(mapping)
        for m in mapping:
            del m[1]
        # print(mapping)
        # print("-------------")

        # [ mapping.pop(1) for m in mapping ]
        # # now we don't need the last item so we can remove
        if mapping and len(mapping) == 2:
            rank_suit_mapping.append([mapping[0][0], mapping[1][0]])
            # print("added")
            # cv2.imwrite('{}-0-split.png'.format(imgC), mapping[0][0])
            # cv2.imwrite('{}-1-split.png'.format(imgC), mapping[1][0])


    return rank_suit_mapping


def eval_rank_suite(rank_suit_mapping, modelRanks, modelSuits):
    # 70x125
    # print(len(rank_suit_mapping))
    c = 0

    pred = []

    for rank, suit in rank_suit_mapping:
        rank = cv2.resize(rank, (100, 120))
        suit = cv2.resize(suit, (100, 120))
        # cv2.imwrite('{}-0.png'.format(c), rank)
        # cv2.imwrite('{}-1.png'.format(c), suit)
        c += 1

        # compare against images
        # bestRank = ""
        # minDiff = 100*120
        # rankDict = dict()
        # for f in os.listdir('imgs/ranks2'):
        #     name = os.path.join('imgs/ranks2', f)
        #     img = cv2.imread(name, cv2.IMREAD_GRAYSCALE)
        #     diff = int(np.sum(cv2.absdiff(img, rank)/255))
        #
        #     rankName = Path(name).stem.split('-')[0]
        #     if rankName in rankDict:
        #         rankDict[rankName] += diff
        #     else:
        #         rankDict[rankName] = diff
        #
        #     if diff < minDiff:
        #         minDiff = diff
        #         bestRank = Path(name).stem

        # bestSuit = ""
        # minDiff = 100*120
        # suitDict = dict()
        # for f in os.listdir('imgs/suits2'):
        #     name = os.path.join('imgs/suits2', f)
        #     img = cv2.imread(name, cv2.IMREAD_GRAYSCALE)
        #     diff = int(np.sum(cv2.absdiff(img, suit)/255))
        #
        #     suitName = Path(name).stem.split('-')[0]
        #     if suitName in suitDict:
        #         suitDict[suitName] += diff
        #     else:
        #         suitDict[suitName] = diff
        #
        #     if diff < minDiff:
        #         minDiff = diff
        #         bestSuit = Path(name).stem


        bestSuit = augtest.model_predict(modelSuits, suit, 'suits')#min(suitDict, key=suitDict.get)
        bestRank = augtest.model_predict(modelRanks, rank, 'ranks')#min(rankDict, key=rankDict.get)



        pred.append('{} of {}'.format(bestRank, bestSuit))
        c+=1

    return pred
#
# [[116, 168]]
# [[102, 346]]
# [[230, 349]]
# [[237, 164]]
def show_text(pred, four_corners_set, img):

    for i in range(0, len(pred)):
        corners = np.array(four_corners_set[i])
        corners_flat = corners.reshape(-1, corners.shape[-1])
        startX = corners_flat[0][0] + 10
        halfY = (corners_flat[0][1] + corners_flat[1][1]) // 2
        pred_list = pred[i].split(' ')

        font = cv2.FONT_HERSHEY_COMPLEX

        cv2.putText(img, pred_list[0], (startX, halfY), font,1,(0,0,0),3,cv2.LINE_AA)
        cv2.putText(img, pred_list[0], (startX, halfY), font,1,(50,200,200),2,cv2.LINE_AA)

        cv2.putText(img, pred_list[1], (startX, halfY+30), font,1,(0,0,0),3,cv2.LINE_AA)
        cv2.putText(img, pred_list[1], (startX, halfY+30), font,1,(50,200,200),2,cv2.LINE_AA)

        cv2.putText(img, pred_list[2], (startX, halfY+60), font,1,(0,0,0),3,cv2.LINE_AA)
        cv2.putText(img, pred_list[2], (startX, halfY+60), font,1,(50,200,200),2,cv2.LINE_AA)

