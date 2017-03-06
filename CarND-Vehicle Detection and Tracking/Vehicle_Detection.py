import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pickle
from skimage.feature import hog
from sklearn.utils import shuffle

from keras.models import Sequential
from keras.models import Model
from keras.layers import ELU
from keras.layers import Input, merge, Convolution2D, MaxPooling2D, UpSampling2D, Lambda
from keras.optimizers import Adam
from keras.layers.pooling import MaxPooling2D
from keras.regularizers import l2
from keras.models import model_from_json
import simplejson as json
from keras.callbacks import ModelCheckpoint
from sklearn.model_selection import train_test_split


### Make data frame in Pandas

import pandas as pd

rootDir = "object-detection-crowdai"
csvFile = pd.read_csv(rootDir+'/labels.csv', header=0)
dataFile = csvFile[(csvFile['Label']!='Pedestrian')].reset_index()
dataFile = dataFile.drop('index', 1)
dataFile = dataFile.drop('Preview URL', 1)
#dataFile['File_Path'] =  rootDir + '/' +dataFile['Frame']
dataFile.head()

train_samples_per_epoch = 2560
valid_samples_per_epoch = 16384
trainBatchSize = 8
validationBatchSize = 8
imgRow = 424
imgCol = 640


def TrainDataGenerator(dataInfo, batchSize, rootDir):
    batch_x, batch_y = [], []
    while True:
        row = 0
        while row < len(dataInfo):

            fileName = './' + rootDir + '/' + dataInfo['Frame'][row]
            # print(fileName, row)
            img = cv2.imread(fileName)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            origShape = img.shape
            img = cv2.resize(img, (imgCol, imgRow))

            data = dataInfo[dataInfo['Frame'][row] == dataInfo['Frame']].reset_index()
            data['xmin'] = np.round(data['xmin'] / origShape[1] * imgCol)
            data['xmax'] = np.round(data['xmax'] / origShape[1] * imgCol)
            data['ymin'] = np.round(data['ymin'] / origShape[0] * imgRow)
            data['ymax'] = np.round(data['ymax'] / origShape[0] * imgRow)

            targetImg = np.reshape(np.zeros_like(img[:, :, 2]), (imgRow, imgCol, 1))
            for i in range(len(data)):
                targetImg[data.iloc[i]['xmax']:data.iloc[i]['ymax'], data.iloc[i]['xmin']:data.iloc[i]['ymin']] = 1
                cv2.rectangle(img, (int(data.iloc[i]['xmin']), int(data.iloc[i]['xmax'])),
                              (int(data.iloc[i]['ymin']), int(data.iloc[i]['ymax'])), (0, 0, 255), 6)
                # print(data.iloc[i]['xmin'],data.iloc[i]['xmax'], data.iloc[i]['ymin'],data.iloc[i]['ymax'])

            row += len(data) - 1

            batch_x.append(img)
            batch_y.append(targetImg)

            if (len(batch_x) == batchSize):
                # yield (np.vstack(batch_x),np.vstack(batch_y))
                x_array = np.asarray(batch_x)
                y_array = np.asarray(batch_y)
                yield (x_array, y_array)
                batch_x, batch_y = [], []
            row += 1


def CreateModel():
    input_layer = Input((imgRow, imgCol, 3))
    conv1 = Convolution2D(16, 3, 3, activation='relu', border_mode='same')(input_layer)
    conv1 = Convolution2D(16, 3, 3, activation='relu', border_mode='same')(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)

    conv2 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(pool1)
    conv2 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(conv2)
    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)

    conv3 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(pool2)
    conv3 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(conv3)
    pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)

    conv4 = Convolution2D(128, 3, 3, activation='relu', border_mode='same')(pool3)
    conv4 = Convolution2D(128, 3, 3, activation='relu', border_mode='same')(conv4)
    pool4 = MaxPooling2D(pool_size=(2, 2))(conv4)

    # conv5 = Convolution2D(512, 3, 3, activation='relu', border_mode='same')(pool4)
    # conv5 = Convolution2D(512, 3, 3, activation='relu', border_mode='same')(conv5)

    up5 = merge([UpSampling2D(size=(2, 2))(conv4), conv3], mode='concat', concat_axis=3)
    conv5 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(up5)
    conv5 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(conv5)

    up6 = merge([UpSampling2D(size=(2, 2))(conv5), conv2], mode='concat', concat_axis=3)
    conv6 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(up6)
    conv6 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(conv6)

    up7 = merge([UpSampling2D(size=(2, 2))(conv6), conv1], mode='concat', concat_axis=3)
    conv7 = Convolution2D(16, 3, 3, activation='relu', border_mode='same')(up7)
    conv7 = Convolution2D(16, 3, 3, activation='relu', border_mode='same')(conv7)

    conv8 = Convolution2D(1, 1, 1, activation='sigmoid')(conv7)

    model = Model(input=input_layer, output=conv8)

    model.compile(optimizer=Adam(lr=1e-4), loss="mse", metrics=['accuracy'])

    return model


model = CreateModel()

trainGenerator = TrainDataGenerator(dataFile, trainBatchSize, rootDir)
# trainGenerator = TrainDataGenerator(trainBatchSize)

weight_save_callback = ModelCheckpoint('./weights/weights.{epoch:02d}-{loss:.4f}.h5', monitor='loss', verbose=2,
                                       save_best_only=False, mode='auto')
model.summary()

print("Created generator and call backs. Starting training")
'''
model.fit_generator(
    trainGenerator,
    samples_per_epoch=train_samples_per_epoch, nb_epoch=40,
    # validation_data=validGenerator,
    # nb_val_samples=valid_samples_per_epoch,
    callbacks=[weight_save_callback],
    verbose=1
)'''

model.save_weights('model.h5', True)
with open('model.json', 'w') as file:
    json.dump(model.to_json(), file)