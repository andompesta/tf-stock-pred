import os
import time

import tensorflow as tf

import model_helper as model
import data_set_helper as data_set
import net_hparams
from models.multi_layer import multi_layer
from models.rnn import rnn
from utils.eval_metric import create_evaluation_metrics

tf.flags.DEFINE_integer("loglevel", 20, "Tensorflow log level")
tf.flags.DEFINE_integer("num_epochs", None, "Number of training Epochs. Defaults to indefinite.")
tf.flags.DEFINE_integer("eval_every", 50, "Evaluate after this many train steps")
tf.flags.DEFINE_string("input_dir", './data', "Evaluate after this many train steps")
FLAGS = tf.flags.FLAGS

TIMESTAMP = int(time.time())
MODEL_DIR = os.path.abspath("./runs_" + str(TIMESTAMP))


COMPANY_NAME = 'goldman'

TRAIN_FILE = os.path.abspath(os.path.join(FLAGS.input_dir, COMPANY_NAME, "train_seq.tfrecords"))
VALIDATION_FILE = os.path.abspath(os.path.join(FLAGS.input_dir, COMPANY_NAME, "valid_seq.tfrecords"))


tf.logging.set_verbosity(FLAGS.loglevel)




def main(unused_argv):
    hparams = net_hparams.create_hparams()

    model_impl = eval(hparams.model_type)

    model_fn = model.create_model_fn(
        hparams,
        model_impl=model_impl)

    estimator = tf.contrib.learn.Estimator(
        model_fn=model_fn,
        model_dir=MODEL_DIR,
        config=tf.contrib.learn.RunConfig(gpu_memory_fraction=0.6,
                                          save_checkpoints_secs=40))

    input_fn_train = data_set.create_input_fn(
        mode=tf.contrib.learn.ModeKeys.TRAIN,
        input_files=[TRAIN_FILE],
        batch_size=hparams.batch_size,
        num_epochs=FLAGS.num_epochs,
        h_params=hparams
    )

    input_fn_eval = data_set.create_input_fn(
        mode=tf.contrib.learn.ModeKeys.EVAL,
        input_files=[VALIDATION_FILE],
        batch_size=hparams.eval_batch_size,
        num_epochs=1,
        h_params=hparams)

    input_fn_infer = data_set.create_input_fn(
        mode=tf.contrib.learn.ModeKeys.INFER,
        input_files=[VALIDATION_FILE],
        batch_size=hparams.eval_batch_size,
        num_epochs=1,
        h_params=hparams)

    eval_metrics = create_evaluation_metrics()

    eval_monitor = tf.contrib.learn.monitors.ValidationMonitor(
        input_fn=input_fn_eval,
        every_n_steps=FLAGS.eval_every,
        metrics=eval_metrics)

    estimator.fit(input_fn=input_fn_train, steps=300000, monitors=[eval_monitor])

    # ev = estimator.predict(input_fn=input_fn_infer)
    # for idx_row, row in enumerate(ev):
    #     print("idx_row {}\t\tprediction {}\t\ttarget {}".format(idx_row, row['predictions'], row['targets']))



if __name__ == "__main__":
    tf.app.run()
