import tensorflow as tf
import utils.summarizer as s
import utils.func_utils as fu

from tensorflow.python.framework import ops
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import nn_ops

def dilatete_trough_time_conv2d(input,
                                filter,
                                strides,
                                padding,
                                rate=None,
                                name=None):
    """Dilatated 2-D convolution.
    Given a 4D input tensor and a filter tensor of shape 
    `[filter_height, filter_width, in_channels, channel_output]`
    Args:
        input: 4-D with shape according to `data_format`.
        filter: 4-D with shape `[filter_height, filter_width, in_channels, channel_multiplier]`.
        strides: 1-D of size 4.  The stride of the sliding window for each dimension of `input`.
        padding: A string, either `'VALID'` or `'SAME'`. The padding algorithm.
      
        rate: 1-D of size 2. The dilation rate in which we sample input values
            across the `height` and `width` dimensions in atrous convolution. If it is
            greater than 1, then all values of strides must be 1.
        name: A name for this operation (optional).
        
    Returns:
        A 4-D `Tensor` with shape according to `data_format`.  E.g., for 
        [batch, out_height, out_width, out_channel].`
    """
    with ops.name_scope(name, "trough_time", [input, filter]) as name:
        input = ops.convert_to_tensor(input, name="tensor_in")
        filter = ops.convert_to_tensor(filter, name="filter_in")
        if rate is None:
            rate = [1, 1]

        def op(input_converted, _, padding):
            return tf.nn.conv2d(
                input=input_converted,
                filter=filter,
                strides=strides,
                padding=padding,
                name=name)

        return nn_ops.with_space_to_batch(
            input=input,
            filter_shape=array_ops.shape(filter),
            dilation_rate=rate,
            padding=padding,
            op=op)



def gated_conv2d_trough_time(x, filter_size, in_channel, out_channel, rate=[1,1], strides=[1, 1, 1, 1], padding="VALID", name="gated_cnn_trough_time"):
    with tf.variable_scope(name) as vs:
        filter_shape = filter_size + [in_channel, out_channel]

        # variable definition
        W = tf.get_variable('weight_filter', shape=filter_shape,
                            initializer=tf.contrib.layers.xavier_initializer_conv2d(),
                            regularizer=None)

        b = tf.get_variable('bias_filter', shape=[out_channel],
                            initializer=tf.constant_initializer(-0.))

        W_t = tf.get_variable('weight_gate', shape=filter_shape,
                              initializer=tf.contrib.layers.xavier_initializer_conv2d())

        b_t = tf.get_variable('bias_gate', shape=out_channel,
                              initializer=tf.constant_initializer(-0.))

        # convolution
        conv_filter = dilatete_trough_time_conv2d(x, W, strides, padding)
        conv_gate = dilatete_trough_time_conv2d(x, W_t, strides, padding)

        conv_filter = tf.add(conv_filter, b)
        conv_gate = tf.add(conv_gate, b_t)

        # gates
        H = tf.tanh(conv_filter, name='activation')
        T = tf.sigmoid(conv_gate, name='transform_gate')

        # debugging
        tf.summary.histogram(vs.name + "_weight_filter", W)
        tf.summary.histogram(vs.name + '_bias_filter', b)
        tf.summary.histogram(vs.name + '_weight_gate', W_t)
        tf.summary.histogram(vs.name + '_bias_gate', b_t)
        s._norm_summary(W, vs.name)
        s._norm_summary(W_t, vs.name)

        return tf.multiply(H, T)


def depthwise_gated_conv1d(x, filter_size, in_channel, channel_multiply,
                          strides=[1, 1, 1, 1],
                          padding="VALID",
                          name="deepwise_gated_cnn",
                          activation_fn=tf.nn.elu,
                          batch_norm=fu.create_BNParams()):
    '''
    Compute a depthwise gated convolution.
    Apply a different filter to every input channel
    :param x: input data -> [mini batch, time_stamp, 1, feature] -> in this way every feature is filtered with a different filter 
    :param filter_size: filter size in time
    :param in_channel: number of input channel
    :param channel_multiply: how many filters to apply to each feature
    :param strides: strides
    :param padding: zero padding
    :param name: scope name
    :param activation_fn: activation function to use
    :param batch_norm: apply batch norm before computing the activation of both W and W_t
    :return: 
    '''
    with tf.variable_scope(name) as vs:
        filter_shape = [1, filter_size, in_channel, channel_multiply]
        # variable definition
        W = tf.get_variable('weight_filter', shape=filter_shape,
                            initializer=tf.contrib.layers.xavier_initializer_conv2d(),
                            regularizer=None)

        W_t = tf.get_variable('weight_gate', shape=filter_shape,
                              initializer=tf.contrib.layers.xavier_initializer_conv2d())

        b_t = tf.get_variable('bias_gate', shape=in_channel*channel_multiply,
                              initializer=tf.constant_initializer(-0.))

        if not batch_norm.apply:
            b = tf.get_variable('bias_filter', shape=[in_channel * channel_multiply],
                                initializer=tf.constant_initializer(-0.))

        # convolution
        conv_filter = tf.nn.depthwise_conv2d(x, W, strides, padding)
        conv_gate = tf.nn.depthwise_conv2d(x, W_t, strides, padding)


        if batch_norm.apply:
            conv_filter_norm = tf.contrib.layers.batch_norm(conv_filter,
                                              center=batch_norm.center,
                                              scale=batch_norm.scale,
                                              is_training=batch_norm.phase,
                                              scope=vs.name + '_bn')
            H = activation_fn(conv_filter_norm, name='activation')
        else:
            conv_filter_linear = tf.add(conv_filter, b)
            H = activation_fn(conv_filter_linear, name='activation')

        conv_gate = tf.add(conv_gate, b_t)
        T = tf.sigmoid(conv_gate, name='transform_gate')

        # debugging
        tf.summary.histogram(vs.name + "_weight_filter", W)
        tf.summary.histogram(vs.name + '_weight_gate', W_t)
        tf.summary.histogram(vs.name + '_bias_gate', b_t)
        if not batch_norm.apply:
            tf.summary.histogram(vs.name + '_bias_filter', b)

        s._norm_summary(W, vs.name + '_filter')
        s._norm_summary(W_t, vs.name + '_gate')
        return tf.multiply(H, T)


def gated_conv1d(x, filter_size, in_channel, out_channel, strides=[1, 1, 1, 1], padding="VALID", name="gated_cnn"):
    with tf.variable_scope(name) as vs:
        filter_shape = [1, filter_size,in_channel, out_channel]
        # variable definition
        W = tf.get_variable('weight_filter', shape=filter_shape,
                            initializer=tf.contrib.layers.xavier_initializer_conv2d(),
                            regularizer=None)

        b = tf.get_variable('bias_filter', shape=[out_channel],
                            initializer=tf.constant_initializer(0.))

        W_t = tf.get_variable('weight_gate', shape=filter_shape,
                              initializer=tf.contrib.layers.xavier_initializer_conv2d())

        b_t = tf.get_variable('bias_gate', shape=out_channel,
                              initializer=tf.constant_initializer(0.))

        # convolution
        conv_filter = tf.nn.conv2d(x, W, strides, padding)
        conv_gate = tf.nn.conv2d(x, W_t, strides, padding)

        conv_filter = tf.add(conv_filter, b)
        conv_gate = tf.add(conv_gate, b_t)

        # gates
        H = tf.tanh(conv_filter, name='activation')
        T = tf.sigmoid(conv_gate, name='transform_gate')

        # debugging
        tf.summary.histogram(vs.name + "_weight_filter", W)
        tf.summary.histogram(vs.name + '_bias_filter', b)
        tf.summary.histogram(vs.name + '_weight_gate', W_t)
        tf.summary.histogram(vs.name + '_bias_gate', b_t)
        s._norm_summary(W, vs.name + '_filter')
        s._norm_summary(W_t, vs.name + '_gate')

        return tf.multiply(H, T)




def highway_conv1d(x, filter_size, in_channel, out_channel, strides=[1, 1, 1, 1], padding="VALID", name="highway_cnn"):
    with tf.variable_scope(name) as vs:
        filter_shape = [1, filter_size, in_channel, out_channel]
        # variable definition
        W = tf.get_variable('weight_filter', shape=filter_shape,
                            initializer=tf.contrib.layers.xavier_initializer_conv2d(),
                            regularizer=None)

        b = tf.get_variable('bias_filter', shape=[out_channel],
                            initializer=tf.constant_initializer(0.))

        W_t = tf.get_variable('weight_gate', shape=filter_shape,
                              initializer=tf.contrib.layers.xavier_initializer_conv2d())

        b_t = tf.get_variable('bias_gate', shape=out_channel,
                              initializer=tf.constant_initializer(-3.))

        # convolution
        conv_filter = tf.nn.conv2d(x, W, strides, padding)
        conv_gate = tf.nn.conv2d(x, W_t, strides, padding)

        conv_filter = tf.add(conv_filter, b)
        conv_gate = tf.add(conv_gate, b_t)

        # gates
        H = tf.tanh(conv_filter, name='activation')
        T = tf.sigmoid(conv_gate, name='transform_gate')
        C = tf.subtract(1.0, T, name='carry_gate')

        # debugging
        tf.summary.histogram(vs.name + "_weight_filter", W)
        tf.summary.histogram(vs.name + '_bias_filter', b)
        tf.summary.histogram(vs.name + '_weight_gate', W_t)
        tf.summary.histogram(vs.name + '_bias_gate', b_t)
        s._norm_summary(W, vs.name)
        s._norm_summary(W_t, vs.name)

        return tf.add(tf.multiply(H, T), tf.multiply(x, C))

def conv1d(x, filter_size, in_channel, out_channel,
           strides=[1,1,1,1],
           padding="VALID",
           name="cnn",
           activation_fn=tf.tanh,
           batch_norm=fu.create_BNParams()):

    with tf.variable_scope(name) as vs:
        filter_shape = [1, filter_size, in_channel, out_channel]
        W = tf.get_variable('kernel', shape=filter_shape)

        if not batch_norm.apply:
            b = tf.get_variable('bias', shape=[out_channel],
                                initializer=tf.constant_initializer(-0.))


        x_filtered = tf.nn.conv2d(x, W, strides, padding)
        if batch_norm.apply:
            activation = tf.contrib.layers.batch_norm(x_filtered,
                                                      center=batch_norm.center,
                                                      scale=batch_norm.scale,
                                                      is_training=batch_norm.phase,
                                                      scope=vs.name + '_bn')
        else:
            activation = tf.add(x_filtered, b)

        if activation_fn:
            activation = activation_fn(activation)

        tf.summary.histogram(vs.name + '_filter', W)
        if not batch_norm.apply:
            tf.summary.histogram(vs.name + '_biases_filter', b)
        s._norm_summary(W, vs.name)
    return activation