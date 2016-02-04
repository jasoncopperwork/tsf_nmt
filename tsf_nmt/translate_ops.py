# -*- coding: utf-8 -*-
from __future__ import print_function

import numpy
import tensorflow as tf
import sys
from tensorflow.python.platform import gfile

import data_utils
from build_ops import create_nmt_model


def decode_from_file(file_path, model_path=None, get_ids=True, FLAGS=None, buckets=None):

    assert FLAGS is not None
    assert buckets is not None

    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:

        # load model parameters.
        model = create_nmt_model(sess, model_path=model_path, forward_only=True,
                                 FLAGS=FLAGS, buckets=buckets, translate=True)

        # Load vocabularies.
        source_vocab_file = FLAGS.data_dir + \
                            (FLAGS.train_data % str(FLAGS.src_vocab_size)) + \
                            ('.vocab.%s' % FLAGS.source_lang)

        target_vocab_file = FLAGS.data_dir + \
                            (FLAGS.train_data % str(FLAGS.tgt_vocab_size)) + \
                            ('.vocab.%s' % FLAGS.target_lang)

        src_vocab, _ = data_utils.initialize_vocabulary(source_vocab_file)
        _, rev_tgt_vocab = data_utils.initialize_vocabulary(target_vocab_file)

        sentence_count = 0

        # Decode from file.
        with gfile.GFile(file_path, mode='r') as source:
            with gfile.GFile(file_path + '.trans', mode='w') as destiny:
                sentence = source.readline()

                while sentence:

                    sentence_count += 1
                    print("Translating sentence %d ", sentence_count)

                    if get_ids:

                        # Get token-ids for the input sentence.
                        token_ids = data_utils.sentence_to_token_ids(sentence, src_vocab)

                    else:

                         # if sentence is already converted, just split the ids
                        token_ids = [int(ss) for ss in sentence.strip().split()]

                    # Get output logits for the sentence.
                    output_hypotheses, output_scores = model.translation_step(sess,
                                                                              token_ids,
                                                                              beam_size=FLAGS.beam_size,
                                                                              dump_remaining=True)

                    outputs = output_hypotheses[0]

                    try:
                        if data_utils.EOS_ID in outputs:
                            outputs = outputs[:outputs.index(data_utils.EOS_ID)]
                    except ValueError:
                        pass

                    # Print out sentence corresponding to outputs.
                    destiny.write(" ".join([rev_tgt_vocab[output] for output in outputs]))
                    destiny.write("\n")
                    sentence = source.readline()


def decode_from_stdin(show_all_n_best=False, FLAGS=None, buckets=None):

    assert FLAGS is not None
    assert buckets is not None

    # with tf.Session(config=tf.ConfigProto(allow_soft_placement=True, log_device_placement=True)) as sess:
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:

        # Create model and load parameters.
        model = create_nmt_model(sess, True, FLAGS, buckets, translate=True)

        # Load vocabularies.
        source_vocab_file = FLAGS.data_dir + \
                            (FLAGS.train_data % str(FLAGS.src_vocab_size)) + \
                            ('.vocab.%s' % FLAGS.source_lang)

        target_vocab_file = FLAGS.data_dir + \
                            (FLAGS.train_data % str(FLAGS.tgt_vocab_size)) + \
                            ('.vocab.%s' % FLAGS.target_lang)

        src_vocab, _ = data_utils.initialize_vocabulary(source_vocab_file)
        _, rev_tgt_vocab = data_utils.initialize_vocabulary(target_vocab_file)

        # Decode from standard input.
        sys.stdout.write("> ")
        sys.stdout.flush()
        sentence = sys.stdin.readline()
        while sentence:

            # Get token-ids for the input sentence.
            token_ids = data_utils.sentence_to_token_ids(sentence, src_vocab)

            # Get output logits for the sentence.
            output_hypotheses, output_scores = model.translation_step(sess, token_ids, beam_size=FLAGS.beam_size, dump_remaining=False)

            outputs = []

            for x in output_hypotheses:
                try:
                    outputs.append(x[:x.index(data_utils.EOS_ID)])
                except ValueError:
                    pass

            output_hypotheses = outputs

            # print translations
            if show_all_n_best:
                for x in xrange(len(outputs)):
                    out = outputs[x]
                    # Print out French sentence corresponding to outputs.
                    print(str(numpy.exp(-output_scores[x])) + "\t" + " ".join([rev_tgt_vocab[output] for output in out]))
            else:
                out = outputs[0]
                # Print out French sentence corresponding to outputs.
                print(str(numpy.exp(-output_scores[0])) + "\t" + " ".join([rev_tgt_vocab[output] for output in out]))

            # wait for a new sentence to translate
            print("> ", end="")
            sys.stdout.flush()
            sentence = sys.stdin.readline()
