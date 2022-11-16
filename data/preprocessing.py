from datetime import datetime

import mne
import numpy as np
from biosppy.signals.ecg import correct_rpeaks, hamilton_segmenter
from mne import make_fixed_length_events
from scipy.interpolate import splev, splrep

import sleep_study as ss

SIGNAL_SCALE = 50000
NUM_WORKER = 8
SN = 3984  # STUDY NUMBER
FREQ = 100
CHANNELS_NO = 4
CHUNK_DURATION = 30.0
OUT_FOLDER = r'C:\Data\preprocessed_ahi_all'
channels = [
    'ECG EKG2-EKG',
    'RESP PTAF',
    'SPO2',
]

POS_EVENT_DICT = {
    "Obstructive Hypopnea": 1,
    "Hypopnea": 1,
    "hypopnea": 1,
    "Mixed Hypopnea": 1,
    "Central Hypopnea": 1,

    "Obstructive Apnea": 2,
    "Central Apnea": 2,
    "Mixed Apnea": 2,
    "apnea": 2,
    "obstructive apnea": 2,
    "central apnea": 2,
    "apnea": 2,
    "Apnea": 2,
}

NEG_EVENT_DICT = {
    'Sleep stage N1': 0,
    'Sleep stage N2': 0,
    'Sleep stage N3': 0,
    'Sleep stage R': 0,
}


mne.set_log_file('log.txt', overwrite=False)


def identity(df):
    return df


def apnea2bad(df):
    df = df.replace(r'.*pnea.*', 'badevent', regex=True)
    print("bad replaced!")
    return df


def wake2bad(df):
    return df.replace("Sleep stage W", 'badevent')


def change_duration(df, label_dict=POS_EVENT_DICT, duration=CHUNK_DURATION):
    for key in label_dict:
        df.loc[df.description == key, 'duration'] = duration
    print("change duration!")
    return df


def calculate_overlap():
    return 0


def preprocess(i, annotation_modifier, out_dir):
    print(str(i) + "---" + str(datetime.now().time().strftime("%H:%M:%S")) + ' --- Processing %d' % i)
    study = ss.data.study_list[i]
    raw = ss.data.load_study(study, annotation_modifier, verbose=True)

    if not all([name in raw.ch_names for name in channels]):
        print("study " + str(study) + " skipped since insufficient channels")
        return 0

    try:
        apnea_events, event_ids = mne.events_from_annotations(raw, event_id=POS_EVENT_DICT, chunk_duration=1.0,
                                                              verbose=None)
    except ValueError:
        print("No Chunk found!")
        return 0

    sfreq = raw.info['sfreq']
    tmax = CHUNK_DURATION - 1. / sfreq
    fixed_events = make_fixed_length_events(raw, id=0, duration=CHUNK_DURATION, overlap=0.)
    epochs = mne.Epochs(raw, fixed_events, event_id=[0], tmin=0, tmax=tmax, baseline=None, preload=True, proj=False,
                        picks=channels, verbose=None)
    epochs.load_data()
    # epochs = epochs.filter(3.0, 45.0, n_jobs=4)
    epochs = epochs.resample(FREQ, npad='auto', n_jobs=NUM_WORKER)
    data = epochs.get_data()

    apnea_events_set = set((apnea_events[:, 0] / sfreq).astype(int))
    starts = (epochs.events[:, 0] / sfreq).astype(int)

    labels = []
    total_event_second = 0
    for seq in range(data.shape[0]):
        epoch_set = set(range(starts[seq], starts[seq] + 30))
        severity_seconds = len(apnea_events_set.intersection(epoch_set))
        labels.append(severity_seconds)
        total_event_second += severity_seconds

    data = process_ECG(data)

    np.savez_compressed(out_dir + '\\' + study + "_" + str(total_event_second), data=data, label=labels)

    return data.shape[0]


def process_ECG(data):
    sleep_epoch_number = data.shape[0]
    SIGNAL_LENGTH = FREQ * CHUNK_DURATION
    ir = 3  # INTERPOLATION RATE(3HZ)
    tm = np.arange(0, 30, step=1 / float(ir))  # TIME METRIC FOR INTERPOLATION

    X = np.zeros((sleep_epoch_number, 90, CHANNELS_NO))

    for i in range(sleep_epoch_number):
        signal = np.squeeze(data[i, 0]) * SIGNAL_SCALE
        rpeaks, = hamilton_segmenter(signal, sampling_rate=FREQ)
        rpeaks, = correct_rpeaks(signal, rpeaks=rpeaks, sampling_rate=FREQ, tol=0.1)

        if 10 < len(rpeaks) < 150:
            rri_tm, rri_signal = rpeaks[1:] / float(FREQ), np.diff(rpeaks) / float(FREQ)
            # rri_signal = medfilt(rri_signal, kernel_size=3)
            ampl_tm, ampl_signal = rpeaks / float(FREQ), signal[rpeaks]
            rri_interp_signal = splev(tm, splrep(rri_tm, rri_signal, k=3), ext=1)
            amp_interp_signal = splev(tm, splrep(ampl_tm, ampl_signal, k=3), ext=1)
            X[i, :, 0] = rri_interp_signal
            X[i, :, 1] = amp_interp_signal

        X[i, :, 2] = np.interp(np.arange(0, SIGNAL_LENGTH, 33.34), np.arange(0, SIGNAL_LENGTH),
                               data[i, 1]) * SIGNAL_SCALE
        X[i, :, 3] = np.interp(np.arange(0, SIGNAL_LENGTH, 33.34), np.arange(0, SIGNAL_LENGTH),
                               data[i, 2]) - 80

    return X


if __name__ == "__main__":
    ss.__init__()
    for i in range(SN):
        preprocess(i, wake2bad, OUT_FOLDER)
