# -*- coding: utf-8 -*-
"""attention.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1XrjPL3O_szhahYZW0z9yhCl9qvIcJJYW
"""

import tensorflow as tf
import os
from tensorflow.python.keras.layers import Layer
from tensorflow.python.keras import backend as K

import numpy as np
import pandas as pd
import re
from bs4 import BeautifulSoup
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from nltk.corpus import stopwords
from tensorflow.keras.layers import Input, LSTM, Embedding, Dense, Concatenate, TimeDistributed
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import ModelCheckpoint
import warnings
pd.set_option("display.max_colwidth", 200)
warnings.filterwarnings("ignore")
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import nltk
nltk.download('punkt') # one time execution
import re
import os
import os
nltk.download("stopwords")

from datasets import load_metric
metric = load_metric("meteor")

from keras import backend as K


contraction_mapping = {"ain't": "is not", "aren't": "are not","can't": "cannot", "'cause": "because", "could've": "could have", "couldn't": "could not", "didn't": "did not",  "doesn't": "does not", "don't": "do not", "hadn't": "had not", "hasn't": "has not", "haven't": "have not", "he'd": "he would","he'll": "he will", "he's": "he is", "how'd": "how did", "how'd'y": "how do you", "how'll": "how will", "how's": "how is", "I'd": "I would", "I'd've": "I would have", "I'll": "I will", "I'll've": "I will have","I'm": "I am", "I've": "I have", "i'd": "i would", "i'd've": "i would have", "i'll": "i will",  "i'll've": "i will have","i'm": "i am", "i've": "i have", "isn't": "is not", "it'd": "it would", "it'd've": "it would have", "it'll": "it will", "it'll've": "it will have","it's": "it is", "let's": "let us", "ma'am": "madam", "mayn't": "may not", "might've": "might have","mightn't": "might not","mightn't've": "might not have", "must've": "must have", "mustn't": "must not", "mustn't've": "must not have", "needn't": "need not", "needn't've": "need not have","o'clock": "of the clock", "oughtn't": "ought not", "oughtn't've": "ought not have", "shan't": "shall not", "sha'n't": "shall not", "shan't've": "shall not have", "she'd": "she would", "she'd've": "she would have", "she'll": "she will", "she'll've": "she will have", "she's": "she is", "should've": "should have", "shouldn't": "should not", "shouldn't've": "should not have", "so've": "so have","so's": "so as", "this's": "this is","that'd": "that would", "that'd've": "that would have", "that's": "that is", "there'd": "there would", "there'd've": "there would have", "there's": "there is", "here's": "here is","they'd": "they would", "they'd've": "they would have", "they'll": "they will", "they'll've": "they will have", "they're": "they are", "they've": "they have", "to've": "to have", "wasn't": "was not", "we'd": "we would", "we'd've": "we would have", "we'll": "we will", "we'll've": "we will have", "we're": "we are", "we've": "we have", "weren't": "were not", "what'll": "what will", "what'll've": "what will have", "what're": "what are", "what's": "what is", "what've": "what have", "when's": "when is", "when've": "when have", "where'd": "where did", "where's": "where is", "where've": "where have", "who'll": "who will", "who'll've": "who will have", "who's": "who is", "who've": "who have", "why's": "why is", "why've": "why have", "will've": "will have", "won't": "will not", "won't've": "will not have", "would've": "would have", "wouldn't": "would not", "wouldn't've": "would not have", "y'all": "you all", "y'all'd": "you all would","y'all'd've": "you all would have","y'all're": "you all are","y'all've": "you all have", "you'd": "you would", "you'd've": "you would have", "you'll": "you will", "you'll've": "you will have", "you're": "you are", "you've": "you have"}


class AttentionLayer(Layer):
    """
    This class implements Bahdanau attention (https://arxiv.org/pdf/1409.0473.pdf).
    There are three sets of weights introduced W_a, U_a, and V_a
     """

    def __init__(self, **kwargs):
        super(AttentionLayer, self).__init__(**kwargs)

    def build(self, input_shape):
        assert isinstance(input_shape, list)
        # Create a trainable weight variable for this layer.

        self.W_a = self.add_weight(name='W_a',
                                   shape=tf.TensorShape((input_shape[0][2], input_shape[0][2])),
                                   initializer='uniform',
                                   trainable=True)
        self.U_a = self.add_weight(name='U_a',
                                   shape=tf.TensorShape((input_shape[1][2], input_shape[0][2])),
                                   initializer='uniform',
                                   trainable=True)
        self.V_a = self.add_weight(name='V_a',
                                   shape=tf.TensorShape((input_shape[0][2], 1)),
                                   initializer='uniform',
                                   trainable=True)

        super(AttentionLayer, self).build(input_shape)  # Be sure to call this at the end

    def call(self, inputs, verbose=False):
        """
        inputs: [encoder_output_sequence, decoder_output_sequence]
        """
        assert type(inputs) == list
        encoder_out_seq, decoder_out_seq = inputs
        if verbose:
            print('encoder_out_seq>', encoder_out_seq.shape)
            print('decoder_out_seq>', decoder_out_seq.shape)

        def energy_step(inputs, states):
            """ Step function for computing energy for a single decoder state """

            assert_msg = "States must be a list. However states {} is of type {}".format(states, type(states))
            assert isinstance(states, list) or isinstance(states, tuple), assert_msg

            """ Some parameters required for shaping tensors"""
            en_seq_len, en_hidden = encoder_out_seq.shape[1], encoder_out_seq.shape[2]
            de_hidden = inputs.shape[-1]

            """ Computing S.Wa where S=[s0, s1, ..., si]"""
            # <= batch_size*en_seq_len, latent_dim
            reshaped_enc_outputs = K.reshape(encoder_out_seq, (-1, en_hidden))
            # <= batch_size*en_seq_len, latent_dim
            W_a_dot_s = K.reshape(K.dot(reshaped_enc_outputs, self.W_a), (-1, en_seq_len, en_hidden))
            if verbose:
                print('wa.s>',W_a_dot_s.shape)

            """ Computing hj.Ua """
            U_a_dot_h = K.expand_dims(K.dot(inputs, self.U_a), 1)  # <= batch_size, 1, latent_dim
            if verbose:
                print('Ua.h>',U_a_dot_h.shape)

            """ tanh(S.Wa + hj.Ua) """
            # <= batch_size*en_seq_len, latent_dim
            reshaped_Ws_plus_Uh = K.tanh(K.reshape(W_a_dot_s + U_a_dot_h, (-1, en_hidden)))
            if verbose:
                print('Ws+Uh>', reshaped_Ws_plus_Uh.shape)

            """ softmax(va.tanh(S.Wa + hj.Ua)) """
            # <= batch_size, en_seq_len
            e_i = K.reshape(K.dot(reshaped_Ws_plus_Uh, self.V_a), (-1, en_seq_len))
            # <= batch_size, en_seq_len
            e_i = K.softmax(e_i)

            if verbose:
                print('ei>', e_i.shape)

            return e_i, [e_i]

        def context_step(inputs, states):
            """ Step function for computing ci using ei """
            # <= batch_size, hidden_size
            c_i = K.sum(encoder_out_seq * K.expand_dims(inputs, -1), axis=1)
            if verbose:
                print('ci>', c_i.shape)
            return c_i, [c_i]

        def create_inital_state(inputs, hidden_size):
            # We are not using initial states, but need to pass something to K.rnn funciton
            fake_state = K.zeros_like(inputs)  # <= (batch_size, enc_seq_len, latent_dim
            fake_state = K.sum(fake_state, axis=[1, 2])  # <= (batch_size)
            fake_state = K.expand_dims(fake_state)  # <= (batch_size, 1)
            fake_state = K.tile(fake_state, [1, hidden_size])  # <= (batch_size, latent_dim
            return fake_state

        fake_state_c = create_inital_state(encoder_out_seq, encoder_out_seq.shape[-1])
        fake_state_e = create_inital_state(encoder_out_seq, encoder_out_seq.shape[1])  # <= (batch_size, enc_seq_len, latent_dim

        """ Computing energy outputs """
        # e_outputs => (batch_size, de_seq_len, en_seq_len)
        last_out, e_outputs, _ = K.rnn(
            energy_step, decoder_out_seq, [fake_state_e],
        )

        """ Computing context vectors """
        last_out, c_outputs, _ = K.rnn(
            context_step, e_outputs, [fake_state_c],
        )

        return c_outputs, e_outputs

    def compute_output_shape(self, input_shape):
        """ Outputs produced by the layer """
        return [
            tf.TensorShape((input_shape[1][0], input_shape[1][1], input_shape[1][2])),
            tf.TensorShape((input_shape[1][0], input_shape[1][1], input_shape[0][1]))
        ]

def text_cleaner(text, num):
    new_string = text.lower()
    new_string = BeautifulSoup(new_string, "lxml").text
    new_string = re.sub(r'\([^)]*\)', '', new_string)
    new_string = re.sub('"','', new_string)
    new_string = ' '.join([contraction_mapping[t] if t in contraction_mapping else t for t in new_string.split(" ")])
    new_string = re.sub(r"'s\b","",new_string)
    new_string = re.sub("[^a-zA-Z]", " ", new_string)
    new_string = re.sub('[m]{2,}', 'mm', new_string)
    if num == 0:
        tokens = [w for w in new_string.split() if not w in stop_words]
    else:
        tokens=new_string.split()
    long_words=[]
    for i in tokens:
        if len(i) > 1:
            long_words.append(i)
    return (" ".join(long_words)).strip()


if __name__ == '__main__':

    # read data from the csv file (from the location it is stored)
    print('reading data')
    Data = pd.read_csv('./data/wikihowAll.csv')
    Data = Data.astype(str)
    rows, columns = Data.shape

    # create a file to record the file names. This can be later used to divide the dataset in train/dev/test sets
    title_file = open('titles.txt', 'wb')

    # The path where the articles are to be saved
    path = "articles"
    if not os.path.exists(path): os.makedirs(path)

    # go over the all the articles in the data file
    for row in range(rows):
        abstract = Data.loc[row,'headline']      # headline is the column representing the summary sentences
        article = Data.loc[row,'text']           # text is the column representing the article

        #  a threshold is used to remove short articles with long summaries as well as articles with no summary
        if len(abstract) < (0.75*len(article)):
            # remove extra commas in abstracts
            abstract = abstract.replace(".,",".")
            abstract = abstract.encode('utf-8')
            # remove extra commas in articles
            article = re.sub(r'[.]+[\n]+[,]',".\n", article)
            article = article.encode('utf-8')


            # a temporary file is created to initially write the summary, it is later used to separate the sentences of the summary
            with open('temporaryFile.txt','wb') as t:
                t.write(abstract)

            # file names are created using the alphanumeric charachters from the article titles.
            # they are stored in a separate text file.
            filename = Data.loc[row,'title']
            filename = "".join(x for x in filename if x.isalnum())
            filename1 = filename + '.txt'
            filename = filename.encode('utf-8')
            title_file.write(filename+b'\n')


            with open(path+'/'+filename1,'wb') as f:
                # summary sentences will first be written into the file in separate lines
                with open('temporaryFile.txt','r') as t:
                    for line in t:
                        line=line.lower()
                        if line != "\n" and line != "\t" and line != " ":
                            f.write(b'@summary'+b'\n')
                            f.write(line.encode('utf-8'))
                            f.write(b'\n')

                # finally the article is written to the file
                f.write(b'@article' + b'\n')
                f.write(article)

    title_file.close()

    f = open('./WikiHow-Dataset/all_train.txt','r')
    directory = './articles'
    train = []
    for line in f.readlines():
        w = open(directory+'/'+line.rstrip()+'.txt','r')
        txt = w.read()
        w.close()
        txt = txt.replace('@summary','')
        pair = re.split('@article',txt)
        pair = list(map(lambda x : re.sub(r"\'s", " \'s", x),pair))
        pair = list(map(lambda x :re.sub(r"n\'t", " n\'t", x),pair))
        pair = list(map(lambda x : re.sub(r"\s{2,}", " ", x), pair))
        pair = list(map(lambda x : x.strip(r"\n"),pair))
        pair = list(map(lambda x : x.strip(),pair))
        pair = list(map(lambda x : x.replace('\n',''),pair))
        train+=[pair]

    f = open('./WikiHow-Dataset/all_test.txt','r')
    directory = './articles'
    test = []
    for line in f.readlines():
        w = open(directory+'/'+line.rstrip()+'.txt','r')
        txt = w.read()
        w.close()
        txt = txt.replace('@summary','')
        pair = re.split('@article',txt)
        pair = list(map(lambda x : re.sub(r"\'s", " \'s", x),pair))
        pair = list(map(lambda x :re.sub(r"n\'t", " n\'t", x),pair))
        pair = list(map(lambda x : re.sub(r"\s{2,}", " ", x), pair))
        pair = list(map(lambda x : x.strip(r"\n"),pair))
        pair = list(map(lambda x : x.strip(),pair))
        pair = list(map(lambda x : x.replace('\n',''),pair))
        test+=[pair]

    print('Checking validation...')

    f = open('./WikiHow-Dataset/all_val.txt','r')
    directory = './articles'
    val = []
    for line in f.readlines():
        w = open(directory+'/'+line.rstrip()+'.txt','r')
        txt = w.read()
        w.close()
        txt = txt.replace('@summary','')
        pair = re.split('@article',txt)
        pair = list(map(lambda x : re.sub(r"\'s", " \'s", x),pair))
        pair = list(map(lambda x :re.sub(r"n\'t", " n\'t", x),pair))
        pair = list(map(lambda x : re.sub(r"\s{2,}", " ", x), pair))
        pair = list(map(lambda x : x.strip(r"\n"),pair))
        pair = list(map(lambda x : x.strip(),pair))
        pair = list(map(lambda x : x.replace('\n',''),pair))
        val+=[pair]

    stop_words = set(stopwords.words('english'))
    df_train = pd.DataFrame(train,columns = ["target","source"])
    df_test = pd.DataFrame(val,columns = ["target","source"])
    cleaned_text = []
    for t in df_train['source']:
        cleaned_text.append(text_cleaner(t,0))

    cleaned_text_test = []
    for t in df_test['source']:
        cleaned_text_test.append(text_cleaner(t,0))

    cleaned_summary = []
    for t in df_train['target']:
        cleaned_summary.append(text_cleaner(t,0))

    cleaned_summary_test = []
    for t in df_test['target']:
        cleaned_summary_test.append(text_cleaner(t,0))

    df_train['cleaned_text'] = cleaned_text
    df_train['cleaned_summary'] = cleaned_summary
    df_test['cleaned_text'] = cleaned_text_test
    df_test['cleaned_summary'] = cleaned_summary_test

    text_word_count = []
    summary_word_count = []

    # populate the lists with sentence lengths
    for i in df_train['cleaned_text']:
        text_word_count.append(len(i.split()))

    for i in df_train['cleaned_summary']:
        summary_word_count.append(len(i.split()))

    length_df = pd.DataFrame({'text':text_word_count, 'summary':summary_word_count})

    cnt=0
    for i in df_train['cleaned_summary']:
        if(len(i.split())<=100):
            cnt=cnt+1
    print(cnt/len(df_train['cleaned_summary']))

    max_text_len = 500
    max_summary_len = 100

    cleaned_text = np.array(df_train['cleaned_text'])
    cleaned_summary = np.array(df_train['cleaned_summary'])

    short_text = []
    short_summary = []

    for i in range(len(cleaned_text)):
        if(len(cleaned_summary[i].split()) <= max_summary_len and len(cleaned_text[i].split()) <= max_text_len):
            short_text.append(cleaned_text[i])
            short_summary.append(cleaned_summary[i])

    df = pd.DataFrame({'text': short_text, 'summary': short_summary})

    cleaned_text_test =np.array(df_test['cleaned_text'])
    cleaned_summary_test =np.array(df_test['cleaned_summary'])

    short_text_test=[]
    short_summary_test=[]

    for i in range(len(cleaned_text_test)):
        if(len(cleaned_summary_test[i].split())<=max_summary_len and len(cleaned_text_test[i].split())<=max_text_len):
            short_text_test.append(cleaned_text_test[i])
            short_summary_test.append(cleaned_summary_test[i])

    df2 = pd.DataFrame({'text':short_text_test,'summary':short_summary_test})

    df['summary'] = df['summary'].apply(lambda x : 'sostok '+ x + ' eostok')
    df2['summary'] = df2['summary'].apply(lambda x : 'sostok '+ x + ' eostok')

    df_sample = df.sample(10000)
    df_test_sample = df2.sample(500)

    x_tr = np.array(df_sample['text'])
    x_val = np.array(df_test_sample['text'])
    y_tr = np.array(df_sample['summary'])
    y_val = np.array(df_test_sample['summary'])

    x_tokenizer = Tokenizer()
    x_tokenizer.fit_on_texts(list(x_tr))

    thresh = 4

    cnt = 0
    tot_cnt = 0
    freq = 0
    tot_freq = 0

    for key,value in x_tokenizer.word_counts.items():
        tot_cnt += 1
        tot_freq += value
        if value < thresh:
            cnt += 1
            freq += value

    print("% of rare words in vocabulary:", (cnt/tot_cnt) * 100)
    print("Total Coverage of rare words:", (freq/tot_freq) * 100)

    #prepare a tokenizer for articles on training data
    x_tokenizer = Tokenizer(num_words=tot_cnt-cnt)
    x_tokenizer.fit_on_texts(list(x_tr))

    #convert text sequences into integer sequences
    x_tr_seq = x_tokenizer.texts_to_sequences(x_tr)
    x_val_seq = x_tokenizer.texts_to_sequences(x_val)

    #padding zero upto maximum length
    x_tr = pad_sequences(x_tr_seq, maxlen=max_text_len, padding='post')
    x_val = pad_sequences(x_val_seq, maxlen=max_text_len, padding='post')

    #size of vocabulary ( +1 for padding token)
    x_voc = x_tokenizer.num_words + 1

    #prepare a tokenizer for summaries on training data
    y_tokenizer = Tokenizer()
    y_tokenizer.fit_on_texts(list(y_tr))

    thresh = 6

    cnt = 0
    tot_cnt = 0
    freq = 0
    tot_freq = 0

    for key,value in y_tokenizer.word_counts.items():
        tot_cnt += 1
        tot_freq += value
        if value < thresh:
            cnt += 1
            freq += value

    print("% of rare words in vocabulary:", (cnt/tot_cnt) * 100)
    print("Total Coverage of rare words:", (freq/tot_freq) * 100)

    #prepare a tokenizer for reviews on training data
    y_tokenizer = Tokenizer(num_words=tot_cnt-cnt)
    y_tokenizer.fit_on_texts(list(y_tr))

    #convert text sequences into integer sequences
    y_tr_seq = y_tokenizer.texts_to_sequences(y_tr)
    y_val_seq = y_tokenizer.texts_to_sequences(y_val)

    #padding zero upto maximum length
    y_tr = pad_sequences(y_tr_seq, maxlen=max_summary_len,
                            padding='post')
    y_val = pad_sequences(y_val_seq, maxlen=max_summary_len,
                            padding='post')

    #size of vocabulary
    y_voc = y_tokenizer.num_words +1

    y_tokenizer.word_counts['sostok'],len(y_tr)

    ind = []
    for i in range(len(y_tr)):
        cnt = 0
        for j in y_tr[i]:
            if j != 0:
                cnt += 1
        if cnt == 2:
            ind.append(i)

    y_tr = np.delete(y_tr,ind, axis=0)
    x_tr = np.delete(x_tr,ind, axis=0)

    ind=[]
    for i in range(len(y_val)):
        cnt = 0
        for j in y_val[i]:
            if j != 0:
                cnt += 1
        if cnt == 2:
            ind.append(i)

    y_val=np.delete(y_val,ind, axis=0)
    x_val=np.delete(x_val,ind, axis=0)

    K.clear_session()

    latent_dim = 100
    embedding_dim= 50

    # Encoder
    encoder_inputs = Input(shape=(max_text_len,))

    #embedding layer
    enc_emb = Embedding(x_voc, embedding_dim,trainable=True)(encoder_inputs)

    #encoder lstm 1
    encoder_lstm1 = LSTM(latent_dim, return_sequences=True,
                return_state=True,dropout=0.4,recurrent_dropout=0.4)
    encoder_output1, state_h1, state_c1 = encoder_lstm1(enc_emb)

    #encoder lstm 2
    encoder_lstm2 = LSTM(latent_dim,return_sequences=True,
                return_state=True,dropout=0.4,recurrent_dropout=0.4)
    encoder_output2, state_h2, state_c2 = encoder_lstm2(encoder_output1)

    #encoder lstm 3
    encoder_lstm3=LSTM(latent_dim, return_state=True,
            return_sequences=True,dropout=0.4,recurrent_dropout=0.4)
    encoder_outputs, state_h, state_c= encoder_lstm3(encoder_output2)

    # Set up the decoder, using `encoder_states` as initial state.
    decoder_inputs = Input(shape=(None,))

    #embedding layer
    dec_emb_layer = Embedding(y_voc, embedding_dim,trainable=True)
    dec_emb = dec_emb_layer(decoder_inputs)

    decoder_lstm = LSTM(latent_dim, return_sequences=True,
            return_state=True,dropout=0.4,recurrent_dropout=0.2)
    decoder_outputs,decoder_fwd_state, decoder_back_state = decoder_lstm(dec_emb,initial_state=[state_h, state_c])

    # Attention layer
    attn_layer = AttentionLayer(name='attention_layer')
    attn_out, attn_states = attn_layer([encoder_outputs, decoder_outputs])

    # Concat attention input and decoder LSTM output
    decoder_concat_input = Concatenate(axis=-1, name='concat_layer')([decoder_outputs, attn_out])

    #dense layer
    decoder_dense = TimeDistributed(Dense(y_voc, activation='softmax'))
    decoder_outputs = decoder_dense(decoder_concat_input)

    # Define the model
    model = Model([encoder_inputs, decoder_inputs], decoder_outputs)

    model.summary()

    model.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy')

    es = EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=5)
    reduce_on_p = ReduceLROnPlateau(monitor="val_loss", factor=0.9, patience=3,
                verbose=1, mode="auto", min_delta=0.0001, cooldown=0, min_lr=0)

    fpath = './models/best_model'
    checkpoint_saver = ModelCheckpoint(fpath, monitor='val_loss',
                    verbose=0, save_best_only=True, save_weights_only=False,
                    mode='auto', period=1)

    history = model.fit(
        [x_tr,y_tr[:,:-1]],
        y_tr.reshape(y_tr.shape[0],y_tr.shape[1], 1)[:,1:],
        epochs=50, callbacks=[es, reduce_on_p, checkpoint_saver], batch_size=128,
        validation_data=(
            [x_val, y_val[:,:-1]], y_val.reshape(y_val.shape[0],y_val.shape[1], 1)[:,1:])
        )
