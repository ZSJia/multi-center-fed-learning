import numpy as np
import os
import tensorflow as tf
import csv

from tensorflow.python import pywrap_tensorflow
from utils.args import parse_args

import pandas as pd

CUSTOM_METRIC_PATH = 'metrics/history.json'

rounds = []
his_acc = []
his_loss = []

def input_fn(data):
    return tf.train.limit_epochs(
          tf.convert_to_tensor(data, dtype=tf.float32), num_epochs=1)   

def restore_ckpt(variable, id, ckpt_path):
    ckpt_file = os.path.join( ckpt_path, "write_%s.ckpt" % id )
    reader = pywrap_tensorflow.NewCheckpointReader( ckpt_file )
    var =  reader.get_tensor( variable ) 
    line = np.array( var ).flatten()
    
    return line   

""" This is the function to generate a point dataset for 
    Tensorflow native clustering 
    
    Note: just discover Kmeans can handle multi-thousands dimensions data,
    so not using a auto encoder any longer and this should boost
    the speed for kmeans per iteration

"""
def get_tensor_from_localmodels(joined_clients, points, variable, client_model):
    def get_variable_by_name(values, dic):
        for var, key in zip(values, dic):
            if key.op.name == variable:
                return np.array(var).flatten()
    
    with client_model.graph.as_default():
        a_dict = tf.trainable_variables()
    for key in joined_clients:
        points[key] = get_variable_by_name(joined_clients[key], a_dict)
        
    return points

def count_num_point_from(learned_cluster):
    val = ""
    for counter, grp in enumerate(learned_cluster):
        val = val + "cluster_%d=%d, " % (counter, grp[0])
    if len(val) > 1 :
        val = val[:-2]
    return val

def save_metric_csv(my_round, micro_acc, stack_list):
    
    args = parse_args()
    
    tot_center = [0., 0., 0., 0.]
    for center in stack_list:
        # This one is a macro acc, we cant compute micro acc here
        # as there is no weights for num samples.
        device_accuracy = np.average([center[k]["accuracy"]  for k in center.keys()])
        device_loss = np.average([center[k]["loss"]  for k in center.keys()])
        device_microf1 = np.average([center[k]["microf1"]  for k in center.keys()])
        device_macrof1 = np.average([center[k]["macrof1"]  for k in center.keys()])
        tot_center[0] += device_accuracy
        tot_center[1] += device_loss
        tot_center[2] += device_microf1
        tot_center[3] += device_macrof1
        
    if len(stack_list) > 1:
        avg_center = [v / len(stack_list) for v in tot_center]
    else:
        avg_center = tot_center

    with open(args.metric_file, 'a+') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow([my_round, micro_acc,
                     avg_center[0], avg_center[1], avg_center[2], avg_center[3]])  
        
def log_history(my_rounds, micro_acc):
    rounds.append(my_rounds)
    his_acc.append(micro_acc)
    
def save_historyfile():
    df = pd.DataFrame({'round': rounds, 'micro-accuracy': his_acc})
    df.to_json(CUSTOM_METRIC_PATH)
    