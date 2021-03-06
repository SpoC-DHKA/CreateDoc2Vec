import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import SGD
import math
from keras.utils.vis_utils import plot_model
import uuid
from polyaxon_client.tracking import Experiment, get_log_level, get_data_paths, get_outputs_path
from polyaxon_client.tracking.contrib.keras import PolyaxonKeras
import argparse

def evaluate(true_y, pred_y):
    true_classes = true_y
        
    CR, CA, PFA, GFA, FR, k = 0, 0, 0, 0, 0, 3.0
    for idx, prediction in enumerate(pred_y):
        # the students answer is correct in meaning and language
        # the system says the same -> accept
        if np.array_equal(true_classes[idx], [1,1]) and prediction == 1:
            CA += 1
        # the system says correct meaning wrong language -> reject
        elif np.array_equal(true_classes[idx], [1,1]) and prediction == 0:
            FR += 1

        # students answer is correct in meaning and wrong in language
        #The system says the same -> reject
        elif np.array_equal(true_classes[idx], [0,1]) and prediction == 0:
            CR += 1
        # the system says correct meaning and correct language -> accept
        elif np.array_equal(true_classes[idx], [0,1]) and prediction == 1:
            PFA += 1

        # students answer is incorrect in meaning and incorrect in language
        # the system says the same -> reject
        elif np.array_equal(true_classes[idx], [0,0]) and prediction == 0:
            CR += 1
        # the system says correct meaning correct language -> accept
        elif np.array_equal(true_classes[idx], [0,0]) and prediction == 1: 
            GFA += 1

    FA = PFA + k * GFA
    Correct = CA + FR
    Incorrect = CR + GFA + PFA
    IncorrectRejectionRate = CR / ( CR + FA + 0.0 )
    CorrectRejectionRate = FR / ( FR + CA + 0.0 )
    # Further metrics
    Z = CA + CR + FA + FR
    Ca = CA / Z
    Cr = CR / Z
    Fa = FA / Z
    Fr = FR / Z

    experiment.log_metrics(CA=CA)
    experiment.log_metrics(CR=CR)
    experiment.log_metrics(FA=FA)
    experiment.log_metrics(FR=FR)

    P = Ca / (Ca + Fa)
    R = Ca / (Ca + Fr)
    SA = Ca + Cr
    F = (2 * P * R)/( P + R)
    
    RCa = Ca / (Fr + Ca)
    RFa = Fa / (Cr + Fa)
    
    D = IncorrectRejectionRate / CorrectRejectionRate
    experiment.log_metrics(D=D)
    print(D)
    Da = RCa / RFa
    Df = math.sqrt((Da*D))
    return Df

experiment = Experiment()

# 0. Read Args
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '--batch_size',
        default=128,
        type=int)

    parser.add_argument(
        '--learning_rate',
        default=0.02,
        type=float)
    
    parser.add_argument(
        '--dropout',
        default=0.2,
        type=float)

    parser.add_argument(
        '--num_epochs',
        default=10,
        type=int)

args = parser.parse_args()
arguments = args.__dict__
batch_size = arguments.pop('batch_size')
learning_rate = arguments.pop('learning_rate')
dropout = arguments.pop('dropout')
num_epochs = arguments.pop('num_epochs')

# 1. Load Data
train_x = np.loadtxt("/data/shared-task/feat80_train_x.csv" ,delimiter='\t', usecols=range(16)[1:], skiprows=1)
train_y = np.loadtxt("/data/shared-task/feat80_train_y.csv", delimiter='\t', usecols=range(3)[1:], skiprows=1)
dev_test_x = np.loadtxt("/data/shared-task/st1_test_x.csv", delimiter='\t', usecols=range(16)[1:], skiprows=1)
dev_test_y = np.loadtxt("/data/shared-task/st1_test_y.csv", delimiter='\t', usecols=range(3)[1:], skiprows=1)

experiment.log_data_ref(data=train_x, data_name='train_x')
experiment.log_data_ref(data=train_y, data_name='train_y')
experiment.log_data_ref(data=dev_test_x, data_name='dev_test_x')
experiment.log_data_ref(data=dev_test_y, data_name='dev_test_y')

# 2. Preporcessing  
seed = 7
np.random.seed(seed)
sc = StandardScaler()
scaled_train_x = sc.fit_transform(train_x)
scaled_dev_test_x = sc.transform(dev_test_x)

# 3. Build the NN
classifier = Sequential()
classifier.add(Dense(64, activation='relu', input_dim=15))
classifier.add(Dropout(0.2))
classifier.add(Dense(64, activation='relu'))
classifier.add(Dropout(dropout))
classifier.add(Dense(1, activation='sigmoid'))
sgd = SGD(lr=learning_rate, decay=1e-6, momentum=0.9, nesterov=True)
classifier.compile(loss='binary_crossentropy',
              optimizer=sgd,
              metrics=['accuracy'])

true_y = []
for (idx, classification) in enumerate(train_y):
    if np.array_equal(classification, [1,1]):
        true_y.append(1)
    else:
        true_y.append(0)

train_y = np.reshape(true_y, (len(true_y), 1))

# 4. Traing the Model
metrics = classifier.fit(scaled_train_x, train_y, batch_size = batch_size, epochs = num_epochs, validation_split=0.1, callbacks=[PolyaxonKeras(experiment=experiment)])

# 5. D-Evaluation
dev_y_pred = classifier.predict_classes(scaled_dev_test_x)
experiment.log_metrics(d_full=evaluate(dev_test_y, dev_y_pred))