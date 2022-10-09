import keras
import tensorflow as tf
from keras import layers
from keras.layers import Conv1D, MaxPooling1D, Reshape, BatchNormalization
from keras.layers import Dense, Flatten, LSTM, Bidirectional
from keras.models import Sequential

p = 30 # patch numbers
l = 100

num_classes = 2
input_shape = (p * l, 1)
image_size = p * l
patch_size = l
num_patches = p
projection_dim = 64
num_heads = 4
transformer_units = [
    projection_dim * 2,
    projection_dim,
]  # Size of the transformer layers
transformer_layers = 1
mlp_head_units = [128, 64, 32]  # [2048, 1024] Size of the dense layers of the final classifier


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
    conved1 = Conv1D(16, kernel_size=50, activation="relu", padding='same')(inputs)
    conved12 = BatchNormalization()(conved1)
    conved11 = MaxPooling1D(pool_size=5)(conved12)
    conved22 = Conv1D(32, kernel_size=20, activation="relu", padding='same')(conved11)
    conved23 = BatchNormalization()(conved22)
    conved55 = MaxPooling1D(pool_size=5)(conved23)
    conv66 = Conv1D(64, kernel_size=10, activation="relu", padding='same')(conved55)

    reshaped = Reshape((30, 4 * 64), input_shape=(120, 64))(conv66)
    encoded_patches = PatchEncoder(num_patches, projection_dim)(reshaped)

    # Create multiple layers of the Transformer block.
    for _ in range(transformer_layers):
        # Layer normalization 1.
        x1 = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
        # Create a multi-head attention layer.
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=projection_dim, dropout=0.1)(x1, x1)
        # Skip connection 1.
        x2 = layers.Add()([attention_output, encoded_patches])
        # Layer normalization 2.
        x3 = layers.LayerNormalization(epsilon=1e-6)(x2)
        # MLP.
        x3 = mlp(x3, hidden_units=transformer_units, dropout_rate=0.1)
        # Skip connection 2.
        encoded_patches = layers.Add()([x3, x2])

    # Create a [batch_size, projection_dim] tensor.
    representation = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
    representation = layers.Flatten()(representation)
    representation = layers.Dropout(0.1)(representation) #change
    # Add MLP.
    features = mlp(representation, hidden_units=mlp_head_units, dropout_rate=0.1) #change
    # Classify outputs.
    logits = layers.Dense(num_classes, activation='softmax')(features)
    # Create the Keras model.
    return keras.Model(inputs=inputs, outputs=logits)


def create_cnn_model():
    model = Sequential()
    model.add(Conv1D(32, kernel_size=50, activation="relu"))
    model.add(MaxPooling1D(pool_size=10))
    model.add(Conv1D(32, kernel_size=20, activation="relu"))
    model.add(MaxPooling1D(pool_size=5))
    model.add(Conv1D(64, kernel_size=10, activation="relu"))

    model.add(Bidirectional(LSTM(128, return_sequences=True)))
    model.add(Flatten())
    model.add(Dense(64, activation="relu"))
    model.add(Dense(32, activation="relu"))
    model.add(Dense(2, activation="softmax"))

    return model