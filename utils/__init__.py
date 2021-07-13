from flask import Flask, request, redirect, url_for,render_template,session, flash
import numpy as np
import pandas as pd
import os
import pickle
from numpy import arange
from collections import OrderedDict
from sklearn.impute import SimpleImputer

ALLOWED_EXTENSIONS = set(['txt', 'csv'])

def load_dataset(path,delimitter,qualifier,assumption = False):
    """
    Read file with given extension.
    If CSV : Read columns with pandas
    if TXT : Read columns manually

    Parameters:
    :path: -- path to the txt file
    :delimitter: -- delimitter for splitting the columns/values
    :assumption: -- if true, assume first line holds the information about valueTypes

    Returns:
    :dataTypes: - return dataTypes list
    :dataColumns: -- return dataColumns list
    :df: -- return dataframe of the file
    """
    if delimitter == "":
        delimitter = ","
    if qualifier == "":
        qualifier = '""'


    extension = path.split(".")[1]
    if(extension == "csv"):
        df = pd.read_csv(path)
        dataTypes = df.dtypes
        dataColumns = df.columns
        return dataTypes,dataColumns,df
    elif(extension == "txt"):
        dataColumns = []
        values = []
        dataTypes = []
        isTypes = assumption
        isColumn = True
        with open(path,mode = "r") as file:
            for line in file:
                # read line and split the columns/types
                line = (line.rstrip('\n')).split(delimitter)
                line = [col.strip(qualifier) for col in line]

                # if value types/columns
                if isTypes:
                    dataTypes = line
                    isTypes = False
                    
                elif isColumn:
                    dataColumns = line
                    isColumn = False

                # if values
                else:
                    values += [line]
        # dataframe is created
        df = pd.DataFrame(data = values, columns = dataColumns)
        #df.set_index(df.columns[0]) :>
        #df.drop([df.columns[0]],inplace=True,axis=1)
        if assumption:
            df = assign_datatypes(df,dataTypes)
        else:
            dataTypes = df.dtypes

        return dataTypes,dataColumns,df

#Check if file is valid
def allowed_file(filename):
    """
    Check if the file is valid.
    
    Parameters:
    :filename: -- path to the file.

    Return true if extension is correct.
    """
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def assign_datatypes(data,dataTypes):
    """
    Change the datatypes in the columns of data with respect to the dataTypes
    Parameters:
    :data: -- given dataframe whose dataTypes are all strings
    :dataTypes: -- given list of data types that determines the types of the data
    """
    for i in range(len(dataTypes)):
        data.iloc[:,i] = data.iloc[:,i].astype(dataTypes[i])
    return data

def choose_attributes(df,attributes):
    """
    Choose the attributes and return the new chosen dataframe.
    Parameters:
    :df: -- given dataframe 
    :attributes: -- features/columns that is picked by the user
    """
    chosen_df = df[attributes]
    unchosen_df = df.drop(attributes,axis=1)
    return chosen_df,unchosen_df

def groupColumns(df):
    dtypeArr = []
    columnArr = []
    lens = []
    returnArr = []
    type_dct = {str(k): list(v) for k, v in df.groupby(df.dtypes, axis=1)}
    type_dct = OrderedDict(sorted(type_dct.items(), key=lambda i: -len(i[1])))

    for types in type_dct:
        type_dct[types].sort()
        columnArr.append(type_dct[types])
        dtypeArr.append(types)
        lens.append(len(type_dct[types]))
    
    for i in range(max(lens)):
        arr = []
        for k in range(len(dtypeArr)):
            if(i < lens[k]):
                arr.append(columnArr[k][i])
        returnArr.append(arr)
    return dtypeArr, returnArr

    
def load_(UPLOAD_FOLDER,files):
    from werkzeug.utils import secure_filename
    if 'file' not in files:
        flash('No file part')
        return None
    file = files['file']

    # check if user does not send any file
    if file.filename == '':
        flash('No selected file')
        return None

    # a valid file is submitted. 
    if file and allowed_file(file.filename):
        # construct the file path
        filename = secure_filename(file.filename)
        file_path = UPLOAD_FOLDER + "\\" + file.filename
        print(file_path)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        # get delimitter and qualifier form the form.
        delimitter = request.form['delimitter']
        qualifier = request.form['qualifier']

        if request.form.get('is-value-type'):
            assumption = True
        else:
            assumption = False

        # read the file and apply the model
        _, _, df = load_dataset(file_path,delimitter=delimitter,qualifier = qualifier, assumption=assumption)
        return df

def concat_columns(data,selected_columns):
    """
    :data: -- Dataframe that will be used
    :selected_columns: -- Selected object columns
    """
    return data[selected_columns].apply(lambda x : ','.join(x.dropna().astype(str)),axis=1)



def check_float(potential_float):
    """
    Check if given expression is float / number.
    """
    try:
        float(potential_float)
        return True
    except ValueError:
        return False

def handle_actions(data,actions):
    """
    Handle the actions and clear the empty inputs and check the errorous inputs.
    
    For object variables -- errorous does not exist
    For continious variables, error can be a non-numerical value
    """
    handled_actions = {}
    
    for col in data.columns:
        action_list = actions[col]
        if data.dtypes[col] == object:
            for i in range(len(action_list)):
                if action_list[i] != "nan":
                    continue
                else:
                    action_list[i] = np.nan
            handled_actions[col] = action_list
            continue
        
        else:
            #Both parameters are empty. No action
            if (action_list[0] == "" and action_list[1] == ""):
                continue
                
            #First parameter is empty. Fill it with minimum (Lower Boundary)
            if (action_list[0] == "") or (check_float(action_list[0]) == False):
                action_list[0] = data[col].min()
                
            else:
                action_list[0] = float(action_list[0])
            
            #Second parameter is empty. Fill it with maximum (Upper Boundary)
            if (action_list[1] == "") or (check_float(action_list[1]) == False):
                action_list[1] = data[col].max()
                
            else:
                action_list[1] = float(action_list[1])
                
            
            handled_actions[col] = action_list
    return handled_actions
    

def filter_data(data, actions):
    """
    Filter the dataset with given boundaries
    :data: -- is the dataframe
    :actions: -- is the list of parameters and the actions that should be taken. 
    """
    copy_data = data.copy()
    handled_actions = handle_actions(data,actions)

    for column, action in handled_actions.items():
        #print(column,action)
        if data.dtypes[column] == object: #Datatype is object/discreate
            condition = data[column].isin(action)
            
        else:
            condition = (data[column] >= action[0]) & (data[column] < action[1])
        data = data[condition]
        print(data.shape)
    return copy_data.loc[data.index]

def remove_temp_files(user_id, head = "temp/"):
    if(user_id == None):
        flash("An error occured while removing files.")
    arr = os.listdir('temp')
    user_files = []
    for file in arr:
        print(file.split("-"))
        if file.split("-")[0] == str(user_id):
            user_files += [file]
    
    print("User files : ",user_files)
    for file in user_files:
        path = head + file
        os.remove(path)

def load_temp_dataframe(user_id, body = "-df-temp",method = "feather",head = "temp/"):
    """
    Load temporary dataframe into temp folder for user. 
    Everytime we need dataframe, reload it.
    :user_id: -- is the id of the user 
    :method: -- how to save , default valeus is feather as it does great job at saving/loading temporary files
    """
    print("(load temp) Called from ",os.getcwd())
    if method == "feather":
        extension = ".feather"
    path = head + str(user_id) + body + extension
    try:
        data = pd.read_feather(path)
    except:
        save_temp_dataframe(pd.DataFrame(),user_id)
        data = pd.read_feather(path)
    data = data.set_index("index") if "index" in data.columns else data
    return data

def save_temp_dataframe(data,user_id, body="-df-temp", method = "feather", head = "temp/"):
    """
    Save temporary dataframe into temp folder for user
    Everytime we change dataframe, change it
    :data: -- dataframe that is changed
    :user_id: -- is the id of the user 
    :method: -- how to save , default valeus is feather as it does great job at saving/loading temporary files
    """
    print("(save temp) Called from ",os.getcwd())
    if method == "feather":
        extension = ".feather"
        path = head + str(user_id) + body + extension
        data = data.reset_index()
        data.to_feather(path)
        
    if method == "csv":
        extension = ".csv"
        path = head + str(user_id) + body + extension
        data.to_csv(path_or_buf = path)


def save_user_model(model,user_id,body = "-model", method = "pickle", head = "models/"):
    if method == "pickle":
        filename = head + str(user_id) + body +  ".sav"
        print("(save model) Called from ",os.getcwd())
        pickle.dump(model, open(filename, 'wb'))

def load_user_model(user_id,body = "-model", method = "pickle",head = "models/"):
    if method == "pickle":
        filename =head + str(user_id) + body + ".sav"
        print("(load model) Called from ",os.getcwd())
        print(filename)
        return pickle.load(open(filename, 'rb'))

def user_log_information(session):
    return ""

def type_divider(df):
    """
    This function takes a dataframe and creates a dict where each key represents type and value of that type
    is array of columns. 

    Input:
    :df: -- Input dataframe 

    Return:
    :type_dict: -- Divided type-columns dictionary
    """
    unique_dtypes = np.unique(df.dtypes.values)
    type_dict = {}
    for dtype in unique_dtypes:
        columns = df.select_dtypes(include = [dtype]).columns
        type_dict[dtype] = columns.values
    return type_dict

def instance_divider(df):
    """
    This function takes a dataframe and outputs a dict with number of columns assigned to each type.
    """
    no_of_integer = df.select_dtypes(include = [np.int8,np.int16,np.int32,np.int64]).shape[1]
    no_of_inexact = df.select_dtypes(include = [np.float16,np.float32,np.float64]).shape[1]
    no_of_object = df.select_dtypes(include = ["object"]).shape[1]
    other_columns = df.shape[1] - (no_of_integer + no_of_inexact + no_of_object)
    return no_of_integer,no_of_inexact,no_of_object,other_columns

def model_chooser(df,selected_y):
    no_of_integer,no_of_inexact,no_of_object,other_columns = instance_divider(df[selected_y])
    print("Cols : ",no_of_integer,no_of_inexact,no_of_object,other_columns)
    if other_columns != 0:
        flash("A variable y with no possible model selection has found!")
        return redirect(url_for("select_y"))
    else:
        if no_of_integer != 0: 
            if no_of_inexact == 0  and no_of_object != 0: #All columns are integer or object, use classification
                classification_model = True
                regression_model = False

            elif no_of_object == 0 and no_of_inexact != 0: # All columns are integer or float, use regression
                regression_model = True 
                classification_model = False
            
            elif no_of_inexact != 0 and no_of_object != 0: #Columns are mixed, show error
                flash("No possible model can be selected! Please use different target variables for prediction")
                return False,False

            else: #All columns are integer. Both of regression and classification can be used
                regression_model = True
                classification_model = True
        else: 
            if no_of_inexact == 0  and no_of_object != 0: #All columns are object, use classification
                classification_model = True
                regression_model = False

            elif no_of_object == 0: # All columns are flaot, use regression
                regression_model = True 
                classification_model = False
    return regression_model,classification_model
