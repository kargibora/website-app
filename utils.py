from preprocess import scale
import numpy as np
import pandas as pd
import os
from flask_wtf import FlaskForm
from collections import OrderedDict
from flask import Flask, request, redirect, url_for,render_template,session, flash
from bokeh.models import ColumnDataSource
from bokeh.resources import INLINE
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.layouts import column, gridplot


from sklearn.preprocessing import OneHotEncoder,LabelEncoder,MinMaxScaler,StandardScaler
from sklearn.impute import SimpleImputer

from math import pi
import pickle
from numpy import arange
from itertools import chain
from collections import OrderedDict
from bokeh.palettes import RdBu as colors
from bokeh.models import ColorBar, LinearColorMapper

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


def scatter_plot(df,x_name,y_name):
#create the graph
    TOOLS = "box_select,lasso_select,pan,wheel_zoom,box_zoom,reset,help,save"
    fig = figure(plot_height=600, plot_width=720, tools = TOOLS)
    source = ColumnDataSource()
    fig.circle(x="x", y="y", source=source, size=5,line_color=None)

    #choose x and y label for plotting
    fig.xaxis.axis_label = x_name
    fig.yaxis.axis_label = y_name
    source.data = dict(
        x = df[x_name],
        y = df[y_name]
    )
    script, div = components(fig)
    #return template
    return render_template(
        'scatter_plot.html',
        plot_script=script,
        plot_div=div,
        js_resources=INLINE.render_js(),
        css_resources=INLINE.render_css(),
        x_name = x_name,
        y_name = y_name,
        graphSelected = True,
        columns = df.columns
    ).encode(encoding='UTF-8')

def scatter_matrix(dataset,features):
    TOOLS = "box_select,lasso_select,pan,wheel_zoom,box_zoom,reset,help,save"
    dataset_selected = dataset[features]
    dataset_source = ColumnDataSource(data=dataset)
    scatter_plots = []
    y_max = len(dataset_selected.columns)-1
    for i, y_col in enumerate(dataset_selected.columns):
        for j, x_col in enumerate(dataset_selected.columns):
            p = figure(plot_width=100, plot_height=100, x_axis_label=x_col, y_axis_label=y_col)
            p.circle(source=dataset_source,x=x_col, y=y_col, fill_alpha=0.3, line_alpha=0.3, size=3)
            if j > 0:
                p.yaxis.axis_label = ""
                p.yaxis.visible = False
                p.y_range = linked_y_range
            else:
                linked_y_range = p.y_range
                p.plot_width=240
            if i < y_max:
                p.xaxis.axis_label = ""
                p.xaxis.visible = False
            else:
                p.plot_height=160
            if i > 0:
                p.x_range = scatter_plots[j].x_range

            scatter_plots.append(p)

    grid = gridplot(scatter_plots, ncols = len(dataset_selected.columns))

    script, div = components(grid)
    return render_template(
    'graphs/scatter_plot.html',
    plot_script=script,
    plot_div=div,
    js_resources=INLINE.render_js(),
    css_resources=INLINE.render_css(),
    x_name = "t1",
    y_name = "t2",
    graphSelected = True,
    columns = dataset.columns
    ).encode(encoding='UTF-8')


def correlation_plot(df,selected_parameters):

    import pandas as pd
    from bokeh.io import output_file, show
    from bokeh.models import BasicTicker, ColorBar, LinearColorMapper, ColumnDataSource, PrintfTickFormatter
    from bokeh.plotting import figure
    from bokeh.transform import transform
    from bokeh.palettes import Viridis256

    # Read your data in pandas dataframe
    data = df[selected_parameters]
    #Now we will create correlation matrix using pandas
    data_corr = data.corr()

    data_corr.index.name = 'AllColumns1'
    data_corr.columns.name = 'AllColumns2'

    # Prepare data.frame in the right format
    data_corr = data_corr.stack().rename("value").reset_index()
    print(selected_parameters)

    # I am using 'Viridis256' to map colors with value, change it with 'colors' if you need some specific colors
    mapper = LinearColorMapper(
        palette=Viridis256, low=data_corr.value.min(), high=data_corr.value.max())

    # Define a figure and tools
    TOOLS = "box_select,lasso_select,pan,wheel_zoom,box_zoom,reset,help,save"
    p = figure(
        tools=TOOLS,
        plot_width=1500,
        plot_height=1250,
        title="Correlation plot",
        x_range=list(data_corr.AllColumns1.drop_duplicates()),
        y_range=list(data_corr.AllColumns2.drop_duplicates()),
        toolbar_location="right",
        x_axis_location="below")

    # Create rectangle for heatmap
    p.rect(
        x="AllColumns1",
        y="AllColumns2",
        width=1,
        height=1,
        source=ColumnDataSource(data_corr),
        line_color=None,
        fill_color=transform('value', mapper))
        
    p.xaxis.major_label_orientation = "vertical"
    # Add legend
    color_bar = ColorBar(
        color_mapper=mapper,
        location=(0, 0),
        ticker=BasicTicker(desired_num_ticks=10))

    p.add_layout(color_bar, 'right')

    path = "temp/" + str(session.get('user_id')) + "-temp.csv"
    data_corr.to_csv(path)

    script, div = components(p)
    return render_template(
    'graphs/correlation_plot.html',
    plot_script=script,
    plot_div=div,
    js_resources=INLINE.render_js(),
    css_resources=INLINE.render_css(),
    graphSelected = True,
    columns = df.columns,
    path = path
    ).encode(encoding='UTF-8')


def create_feature_matrix(data,parameters):
    """
    Create feature matrix with objects. Example:
    If parameters = [gender,eye]
    Resulting list should be [[M,LEFT],[M,RİGHT],[W,LEFT],[W,RİGHT]]
    """
    import itertools 

    unique_list = []
    for parameter in parameters: # Collect unique parameters
        unique_list += [data[parameter].unique()]


    all_parameter_permutations = list(itertools.product(*unique_list)) # Create permutation of features
    result = []
    for permutation in all_parameter_permutations: #Find the count of all conditions
        condition = np.full(len(data),True)
        name = ""
        for i in range(len(parameters)):
            condition = (condition & (data[parameters[i]] == permutation[i]))
            name += (parameters[i] + "=" + str(permutation[i]) + ",")
        result += [[name,data.loc[condition].shape[0]]]
    return result   

def pie_plot(data,selected_parameter, sort_by_values = False):
    from math import pi 
    from bokeh.transform import cumsum 
    from bokeh.palettes import inferno
    result = create_feature_matrix(data,selected_parameter)
    df_pie_agg = pd.DataFrame(result,columns = ["Parameter","Count"])
    
    # Add angles based on Win Count so each wedge is the right size
    df_pie_agg['Angle'] = df_pie_agg['Count']/df_pie_agg['Count'].sum() * 2*pi
    df_pie_agg['color'] = inferno(df_pie_agg.shape[0])
    
    if sort_by_values:
        df_pie_agg = df_pie_agg.sort_values(by = 'Count', ascending = False)

    TOOLS = "box_select,lasso_select,pan,wheel_zoom,box_zoom,reset,help,save"
    # Draw a chart
    p = figure(title='Pie Chart', x_range=(-0.5, 1.0),
            plot_width=800, plot_height=600,tools = TOOLS, 
            toolbar_location="below", tooltips="@Parameter: @{Count}") 

    p.wedge(x=0.1, y=1, radius=0.4,
            start_angle=cumsum('Angle', include_zero=True), 
            end_angle=cumsum('Angle'),
            line_color="white", 
            legend='Parameter', 
            fill_color = 'color',
            source=df_pie_agg)

    # These options can be used to make the chart cleaner
    #p.axis.axis_label=None
    #p.axis.visible=False
    #p.grid.grid_line_color = None
    #p.outline_line_color = None
    path = "temp/" + str(session.get('user_id')) + "-temp.csv"

    df_pie_agg.to_csv(path)
    script, div = components(p)
    return render_template(
    'graphs/pie_plot.html',
    plot_script=script,
    plot_div=div,
    js_resources=INLINE.render_js(),
    css_resources=INLINE.render_css(),
    graphSelected = True,
    selected = selected_parameter,
    columns = data.columns,
    path = path
    ).encode(encoding='UTF-8')

def dist_plot(df,parameter,bins = 20):
    
    # Use numpy to create histogram bins
    hist, edges = np.histogram(df[parameter], bins=bins)
    TOOLS = "box_select,lasso_select,pan,wheel_zoom,box_zoom,reset,help,save"
    # Draw a chart
    p = figure(title='Histogram', plot_width=800, plot_height=600,
            x_axis_label=parameter, y_axis_label='Count', tools = TOOLS)

    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], line_color='white', fill_color='black')


    path = "temp/" + str(session.get('user_id')) + "temp.csv"
    pd.DataFrame(np.c_[hist,edges[:-1]],columns = ["hist","edges"]).to_csv(path)

    script, div = components(p)
    return render_template(
    'graphs/dist_plot.html',
    plot_script=script,
    plot_div=div,
    js_resources=INLINE.render_js(),
    css_resources=INLINE.render_css(),
    graphSelected = True,
    columns = df.columns,
    selected = parameter,
    path=path
    ).encode(encoding='UTF-8')

def nan_plot(df):
    return "Show Nan"


def bar_plot(data,selected_parameter, option = 'Vertical'):

    # Draw a chart
    TOOLS = "box_select,lasso_select,pan,wheel_zoom,box_zoom,reset,help,save"
    result = create_feature_matrix(data,selected_parameter)
    df_pie_agg = pd.DataFrame(result,columns = ["Parameter","Count"])
    print(df_pie_agg['Parameter'])

    if option == 'Vertical':
        p = figure(title='Vertical Bar Chart', x_range=df_pie_agg["Parameter"], 
                plot_width=900, plot_height=600,
                y_axis_label='Count',tooltips="@Parameter: @{Count}",tools = TOOLS)

        p.vbar(x="Parameter", width = 0.75, bottom=0, top= "Count", 
            fill_color='black', line_color='white',source = df_pie_agg)

    else:
        p = figure(title='Horizontal Bar Chart', y_range=df_pie_agg["Parameter"], 
                plot_width=900, plot_height=600,
                y_axis_label='Count',tooltips="@Parameter: @{Count}", tools = TOOLS)

        p.hbar(y="Parameter",height = 0.75, left=0, right= "Count", 
            fill_color='black', line_color='white',source = df_pie_agg)


        
    p.xaxis.major_label_orientation = 1.57
    script, div = components(p)

    path = "temp/" + str(session.get('user_id')) + "-temp.csv"
    df_pie_agg.to_csv(path)
    
    return render_template(
    'graphs/bar_plot.html',
    plot_script=script,
    plot_div=div,
    js_resources=INLINE.render_js(),
    css_resources=INLINE.render_css(),
    graphSelected = True,
    columns = data.columns,
    selected = selected_parameter,
    path=path
    ).encode(encoding='UTF-8')
    


def return_result_graph(model,selectedModel):
    """
    Parameters:
    :model: -- Is the model that is trained
    :selectedModel: -- Return the graph with respect to the selected model

    Steps:
    Display the result screen with graph. Return template with
        *) Graph of the train/valid-data-metric
        *) Upload file is now reachable
    """
    return None

def proccess_and_show(model,testX,selectedX,selectedY,selectedModel):
    """
    Parameters:
    :model: -- Is the model that is trained
    :testX: -- Test, unproccess data for our machine learning model
    :yExist: -- If yExist, also show the predictions vs real result
    :selectedModel: -- Preprocess with respect to the selectedModel

    Steps:
    1)Preprocess the given data and predict it with model.
    2)Return template with 
        *) Graph of the test-data-metric 
        *) Prediction of the test-data

    """
    return None

def PCA_transformation(data, reduce_to = None, var_ratio = None):
    """
    Parameters:
    :data: -- Dataframe that is given
    :reduce_to: -- The final dimension after PCA transformation
    :var_ratio: -- If given, reduce until
    Apply Principal Component Analysis (PCA) to Dataset.
    Dataset is first standirtized. Then Dataset is reduced to n = reduce_to-D dimension. 
    If the data has an object column, error should be given. Or assume that it is intended and reduce the only numerical columns
    Optional : if 
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA

    if reduce_to == None:
        reduce_to = 0.80 # -- default ratio value
    
    # Ready the dataset and variables
    if var_ratio != None:
        if var_ratio <= 1 and var_ratio >= 0:
            reduce_to = var_ratio
        else:
            print("Error..")
            return None


    numerical_df = data.select_dtypes(exclude = ["object"])
    scaler = StandardScaler()
    pca = PCA(n_components=reduce_to)

    # Standirtize
    numerical_df = scaler.fit_transform(numerical_df)

    # PCA Analysis
    pca.fit(numerical_df)
    reduced_df = pca.transform(numerical_df)

    # Return dataframe
    column_names = ["var" + str(i) for i in range(0,reduced_df.shape[1])]
    reduced_df = pd.DataFrame(reduced_df,columns = column_names)
    return reduced_df,pca

def PCA_transformation_describe(new_df,pca):
    """
    Return a line graph by using bokeh. 
    :pca: -- pca module that contains variance ratios
    :new_df: -- df that is newly transformed
    """

    #Create the graph
    p = figure(title = "Variance Ratio", plot_width = 1200,plot_height = 800,
    x_axis_label = "Number of components",y_axis_label = "Cumilative Ratio")
    
    line_y = np.cumsum(pca.explained_variance_ratio_)
    line_x = range(1,len(line_y)+1)
    df_line = pd.DataFrame()
    np.cumsum(pca.explained_variance_ratio_)
    p.line(x = line_x, y = line_y, color = "black", line_width = 2 )
    script, div = components(p)

    return render_template(
    'transformation/pca_transform.html',
    plot_script=script,
    plot_div=div,
    js_resources=INLINE.render_js(),
    css_resources=INLINE.render_css(),
    graphSelected = True,
    ).encode(encoding='UTF-8')
    #Extra information


def concat_columns(data,selected_columns):
    """
    :data: -- Dataframe that will be used
    :selected_columns: -- Selected object columns
    """
    return data[selected_columns].apply(lambda x : ','.join(x.dropna().astype(str)),axis=1)


def combine_columns(data, selected_columns, new_column_name, mode, delete_column = True):
    """
    Parameters:
    :data: -- Dataframe that is given
    :selected_columns: -- Subset of the features that will be combined into a single column.
    :new_column_name: -- Name of the new column:
    :mode: -- Which operation will be used
        *) mode = mean -- sum the columns and take avarage of it
        *) mode = sum -- sum the columns
        *) mode = differnce -- take the difference of the columns. Two columns must be selected.
        *) mode = concat -- concat the object columns. An example could be [M,F],[Left,Right] -> MLeft,MRight,FLeft,FRight

    :delete_column: -- If true, discard the used columns. 
    """
    selected_df = data[selected_columns]

    if mode == "mean":
        data[new_column_name] = selected_df.sum(axis = 1)/len(selected_columns)
        
    elif mode == "sum":
        data[new_column_name] = selected_df.sum(axis = 1)

    elif mode == "difference":
        data[new_column_name] = selected_df.iloc[:,0] - selected_df.iloc[:,1]

    elif mode == "concat": 
        concated_columns = concat_columns(data,selected_columns)
        data[new_column_name] = concated_columns 

    elif mode == "drop-nan-rows":
        data = selected_df.dropna()

    elif mode == "drop-nan-columns":
        data = selected_df.dropna(axis=1)

    elif mode == "min-max-scale":
        #Check if columns are numeric
        selected_df = selected_df.select_dtypes(include = ["number"])
        selected_columns = selected_df.columns
        scaled_df,scaler = min_max_scale(selected_df)
        data[selected_columns] = scaled_df
        return data,scaler

    elif mode == "object-encode":
        #Check if columns are object
        selected_df = selected_df.select_dtypes(include = ["object"])
        selected_columns = selected_df.columns
        encoded_df,encoder = object_encode(selected_df)
        data[selected_columns] = encoded_df
        return data,encoder

    elif mode == "onehot-encode":
        #Check if columns are discreate or object
        selected_df = selected_df.select_dtypes(exclude = ["float32","float64"])
        selected_columns = selected_df.columns
        encoded_df, encoder = onehot_encode(selected_df)
        for col in encoded_df.columns:
            data[col] = encoded_df[col]
        return data,encoder

    elif mode == "drop-columns":
        data.drop(selected_columns,axis=1,inplace=True), 
        
    elif mode == "standard-scale":
        #Check if columns are numeric
        selected_df = selected_df.select_dtypes(include = ["number"])
        selected_columns = selected_df.columns
        scaled_df, scaler = standard_scale(selected_columns)
        data[selected_columns] = scaled_df
        return data,scaler

    elif mode == "impute-columns-median":
        imputer = SimpleImputer(strategy = "mean")
        selected_df = selected_df.select_dtypes(include = ["number"])
        selected_columns = selected_df.columns
        imputed_df = imputer.fit_transform(selected_df)
        data[selected_columns] = imputed_df


    elif mode == "impute-columns-mean":
        imputer = SimpleImputer(strategy = "median")
        selected_df = selected_df.select_dtypes(include = ["number"])
        selected_columns = selected_df.columns
        imputed_df = imputer.fit_transform(selected_df)
        data[selected_columns] = imputed_df

    
    elif mode == "impute-columns-mfq":
        imputer = SimpleImputer(strategy = "most_frequent")
        imputed_df = imputer.fit_transform(selected_df)
        data[selected_columns] = imputed_df


    if delete_column and mode in ["sum","mean","difference","concat"]:
        return data.drop(selected_columns,axis = 1),None
    
    return data,None

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

def remove_temp_files(user_id):
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
        path = "temp/" + file
        os.remove(path)

def load_temp_dataframe(user_id, body = "-df-temp",method = "feather"):
    """
    Load temporary dataframe into temp folder for user. 
    Everytime we need dataframe, reload it.
    :user_id: -- is the id of the user 
    :method: -- how to save , default valeus is feather as it does great job at saving/loading temporary files
    """
    if method == "feather":
        extension = ".feather"
    path = "temp/" + str(user_id) + body + extension
    try:
        data = pd.read_feather(path)
    except:
        save_temp_dataframe(pd.DataFrame(),user_id)
        data = pd.read_feather(path)
    data = data.set_index("index") if "index" in data.columns else data
    return data

def save_temp_dataframe(data,user_id, body="-df-temp", method = "feather" ):
    """
    Save temporary dataframe into temp folder for user
    Everytime we change dataframe, change it
    :data: -- dataframe that is changed
    :user_id: -- is the id of the user 
    :method: -- how to save , default valeus is feather as it does great job at saving/loading temporary files
    """
    if method == "feather":
        extension = ".feather"
        path = "temp/" + str(user_id) + body + extension
        data = data.reset_index()
        data.to_feather(path)
    if method == "csv":
        extension = ".csv"
        path = "temp/" + str(user_id) + body + extension
        data.to_csv(path_or_buf = path)


def calculate_model_no(user_id):
    if(user_id == None):
        flash("An error occured while load/saving model.")
    arr = os.listdir('models')
    user_models = []
    for model in arr:
        print(model.split("-"))
        if model.split("-")[0] == str(user_id):
            user_models += [model]
    
    print("User models : ",user_models)
    return len(user_models)

def save_user_model(model,user_id,body = "-model", method = "pickle"):
    if method == "pickle":
        #model_no = calculate_model_no(user_id)
        filename = "models/" + str(user_id) + body +  ".sav"
        pickle.dump(model, open(filename, 'wb'))

def load_user_model(user_id,body = "-model", method = "pickle"):
    if method == "pickle":
        #model_no = calculate_model_no(user_id)
        filename = "models/" + str(user_id) + body + ".sav"
        return pickle.load(open(filename, 'rb'))

def user_log_information(session):
    return "[Workspace : {}, Selected Data : {}]".format(session.get("selected_workspace"),session.get("selected_dataframe"))


def min_max_scale(df,object_prefix = None):
    """
    :df: -- is the dataframe with values that will be scaled
    :object_prefix: -- if provided, add prefix to every column name
    """
    if df.empty:
        return df,None
    scaler = MinMaxScaler()
    original_columns = df.columns
    try:
        df = scaler.fit_transform(df)
    except:
        flash("An error has occured!")
        return df,None

    if object_prefix is not None:
        original_columns = [object_prefix + col for col in original_columns]

    return pd.DataFrame(df,columns = original_columns),scaler

def standard_scale(df,object_prefix = None):
    """
    Inputs:
    :df: -- is the dataframe with values that will be scaled
    :object_prefix: -- if provided, add prefix to every column name

    Returns:
    :dataframe object: -- Dataframe object with scaled columns
    :scaler: -- Scaler used in scaling.
    """
    if df.empty:
        return df,None
    scaler = StandardScaler()
    original_columns = df.columns
    try:
        df = scaler.fit_transform(df)
    except:
        flash("An error has occured!")
        return df,None
        
    if object_prefix is not None:
        original_columns = [object_prefix + col for col in original_columns]

    return pd.DataFrame(df,columns = original_columns),scaler

def object_encode(df,object_prefix = None):
    """
    :df: -- is the dataframe with values that will be scaled
    :object_prefix: -- if provided, add prefix to every column name
    """
    if df.empty:
        return df,None
    encoder = LabelEncoder()
    original_columns = df.columns
    try:
        df = encoder.fit_transform(df)
    except:
        flash("En error has occured!")
        return df,None
    
    if object_prefix is not None:
        original_columns = [object_prefix + col for col in original_columns]
    return pd.DataFrame(df,columns = original_columns),encoder

def onehot_encode(df,object_prefix = None):
    """
    :df: -- is the dataframe with values that will be scaled
    :object_prefix: -- if provided, add prefix to every column name
    """
    encoder = OneHotEncoder()
    original_columns = df.columns
    try:
        df = encoder.fit_transform(df).toarray()
    except:
        flash("En error has occured!")
        return None
    
    encoded_columns = encoder.get_feature_names(original_columns)
    print("Encoded columns are : ",encoded_columns)
    print(df)
    if object_prefix is not None:
        encoded_columns = [object_prefix + col for col in encoded_columns]
    return pd.DataFrame(df,columns = encoded_columns),encoder

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