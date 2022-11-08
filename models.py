import keras
import tensorflow as tf
from keras import layers
from keras.layers import Conv1D, MaxPooling1D, Reshape, BatchNormalization, GRU
from keras.layers import Dense, Flatten, LSTM, Bidirectional, UpSampling1D
from keras.models import Sequential

p = 90  # patch numbers
l = 1
ch = 4
num_classes = 2
input_shape = (p * l, ch)
image_size = p * l
patch_size = l
num_patches = p
projection_dim = 16 #16
num_heads = 4
transformer_units = [
    projection_dim * 2,
    projection_dim,
]  # Size of the transformer layers
transformer_layers = 3
mlp_head_units = [1024, 256]  # [2048, 1024] Size of the dense layers of the final classifier


########################################################################################################################

def mlp(x, hidden_units, dropout_rate):
    for units in hidden_units:
        x = layers.Dense(units, activation=tf.nn.gelu)(x)
        x = layers.Dropout(dropout_rate)(x)
    return x


class PatchEncoder(layers.Layer):
    def __init__(self, num_patches, projection_dim):
        super(PatchEncoder, self).__init__()
        self.num_patches = num_patches
        self.projection = layers.Dense(units=projection_dim)
        self.position_embedding = layers.Embedding(
            input_dim=num_patches, output_dim=projection_dim
        )

    def call(self, patch):
        positions = tf.range(start=0, limit=self.num_patches, delta=1)
        encoded = self.projection(patch) + self.position_embedding(positions)
        return encoded


def create_vit_classifier():
    inputs = layers.Input(shape=input_shape)

    reshaped = Reshape((p, -1))(inputs)

    encoded_patches = PatchEncoder(num_patches, projection_dim)(reshaped)

    # Create multiple layers of the Transformer block.
    for _ in range(transformer_layers):
        # Layer normalization 1.
        x1 = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
        # Create a multi-head attention layer.
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=projection_dim, dropout=0.25)(x1, x1)
        # Skip connection 1.
        x2 = layers.Add()([attention_output, encoded_patches])
        # Layer normalization 2.
        x3 = layers.LayerNormalization(epsilon=1e-6)(x2)
        # MLP.
        x3 = mlp(x3, hidden_units=transformer_units, dropout_rate=0.25)
        # Skip connection 2.
        encoded_patches = layers.Add()([x3, x2])

    # Create a [batch_size, projection_dim] tensor.
    representation = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
    representation = layers.Flatten()(representation)
    representation = layers.Dropout(0.25)(representation)  # change
    # Add MLP.
    features = mlp(representation, hidden_units=mlp_head_units, dropout_rate=0.5)  # change
    # Classify outputs.
    logits = layers.Dense(num_classes, activation='softmax')(features)
    # Create the Keras model.
    return keras.Model(inputs=inputs, outputs=logits)


def create_cnn_model():
    model = Sequential()
    model.add(Conv1D(32, kernel_size=8, activation="relu", padding='same', name='l1'))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Conv1D(32, kernel_size=4, activation="relu", padding='same', name='l2'))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Conv1D(64, kernel_size=2, activation="relu", padding='same', name='l3'))

    model.add(Bidirectional(LSTM(64, return_sequences=True)))
    model.add(Flatten())
    model.add(Dense(64, activation="relu"))
    model.add(Dense(32, activation="relu"))
    model.add(Dense(2, activation="softmax"))

    return model

def create_model():
    model = Sequential()
    model.add(GRU(128, return_sequences=True))
    model.add(GRU(32, return_sequences=True))
    model.add(GRU(8, return_sequences=True))

    model.add(Flatten())
    model.add(Dense(8, activation="relu"))
    model.add(Dense(2, activation="softmax"))

    return model


def create_ed_cnn_model():
    model = Sequential()
    model.add(Conv1D(16, kernel_size=50, activation="relu", padding='same', name='l1'))
    model.add(MaxPooling1D(pool_size=10))
    model.add(Conv1D(32, kernel_size=20, activation="relu", padding='same', name='l2'))
    model.add(MaxPooling1D(pool_size=5))
    model.add(Conv1D(64, kernel_size=10, activation="relu", padding='same', name='l3'))

    model.add(UpSampling1D(size=10))
    model.add(Conv1D(8, kernel_size=10, activation="relu", padding='same'))
    model.add(UpSampling1D(size=5))
    model.add(Conv1D(1, kernel_size=10, activation="relu", padding='same'))

    return model

def create_baseline_model(type):
    model = Sequential()

    if type == "LSTM":
        model.add(LSTM(64, return_sequences=True))
        model.add(LSTM(32, return_sequences=True))
        model.add(LSTM(16, return_sequences=True))

        model.add(Flatten())
        model.add(Dense(4, activation="relu"))
        model.add(Dense(2, activation="softmax"))
    elif type == "CNN":
        model.add(Conv1D(64, kernel_size=256, activation='relu', padding='same'))
        model.add(Conv1D(32, kernel_size=64, activation='relu', padding='same'))
        model.add(Conv1D(16, kernel_size=64, activation="relu", padding='same'))

        model.add(Flatten())
        model.add(Dense(4, activation="relu"))
        model.add(Dense(2, activation="softmax"))
    return model

