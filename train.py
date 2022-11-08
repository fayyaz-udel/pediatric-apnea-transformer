import pickle

import keras
import numpy as np
from keras.callbacks import LearningRateScheduler, EarlyStopping
from sklearn.metrics import confusion_matrix, f1_score

from models import create_vit_classifier, create_baseline_model


def lr_schedule(epoch, lr):
    if epoch > 50 and (epoch - 5) % 10 == 0:
        lr *= 0.5
    print("Learning rate: ", lr)
    return lr


if __name__ == "__main__":
    # x0, y0 = get_all_data(r"C:\Data\preprocessed_three_bypatient\f0")
    # x1, y1 = get_all_data(r"C:\Data\preprocessed_three_bypatient\f1")
    # x2, y2 = get_all_data(r"C:\Data\preprocessed_three_bypatient\f2")
    # x3, y3 = get_all_data(r"C:\Data\preprocessed_three_bypatient\f3")
    # x4, y4 = get_all_data(r"C:\Data\preprocessed_three_bypatient\f4")
    #
    # x = [x0, x1, x2, x3, x4]
    # y = [y0, y1, y2, y3, y4]
    #
    # with open('objs_foldPat.pkl', 'wb') as f:
    #      pickle.dump([x, y], f)

    with open('objs_foldPat.pkl', 'rb') as f:
        x, y = pickle.load(f)

    ACC = []
    SN = []
    SP = []
    F2 = []

for fold in range(5):

    first = True
    for i in range(5):
        if i == fold:
            x_test = x[i]
            y_test = y[i]
        else:
            if first:
                x_train = x[i]
                y_train = y[i]
                first = False
            else:
                x_train = np.concatenate((x_train, x[i]))
                y_train = np.concatenate((y_train, y[i]))

    y_train = keras.utils.to_categorical(y_train, num_classes=2)
    y_test = keras.utils.to_categorical(y_test, num_classes=2)

    model = create_vit_classifier()
    #model = create_baseline_model("LSTM")

    opt = keras.optimizers.Adam()
    model.compile(optimizer=opt, loss=keras.losses.CategoricalCrossentropy(), metrics=['accuracy'])

    lr_scheduler = LearningRateScheduler(lr_schedule)
    early_stopper = EarlyStopping(patience=50, restore_best_weights=True)
    # history = model.fit(x=x_train, y=y_train, batch_size=256, epochs=20, validation_split=0.1)
    history = model.fit(x=x_train, y=y_train, batch_size=256, epochs=500, validation_split=0.1,
                       callbacks=[early_stopper, lr_scheduler])
    loss, accuracy = model.evaluate(x_test, y_test)
    y_score = model.predict(x_test)
    y_predict = np.argmax(y_score, axis=-1)
    y_training = np.argmax(y_test, axis=-1)

    # Confusion matrix:
    C = confusion_matrix(y_training, y_predict, labels=(1, 0))
    TP, TN, FP, FN = C[0, 0], C[1, 1], C[1, 0], C[0, 1]
    acc, sn, sp = 1. * (TP + TN) / (TP + TN + FP + FN), 1. * TP / (TP + FN), 1. * TN / (TN + FP)
    f1 = f1_score(y_training, y_predict)

    ACC.append(acc * 100)
    SN.append(sn * 100)
    SP.append(sp * 100)
    F2.append(f1 * 100)

print(ACC)
print(SN)
print(SP)
print(F2)
print("Accuracy: %.2f -+ %.3f" % (np.mean(ACC), np.std(ACC)))
print("Sensitivity: %.2f -+ %.3f" % (np.mean(SN), np.std(SN)))
print("Specifity: %.2f -+ %.3f" % (np.mean(SP), np.std(SP)))
print("F1: %.2f -+ %.3f" % (np.mean(F2), np.std(F2)))
