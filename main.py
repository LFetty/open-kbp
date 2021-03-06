import shutil

import numpy as np

from provided_code.data_loader import DataLoader
from provided_code.dose_evaluation_class import EvaluateDose
from provided_code.general_functions import get_paths, make_directory_and_return_path
from provided_code.network_functions import PredictionModel

if __name__ == '__main__':
    # Define project directories
    # TODO: Must define the path of where the data is stored.
    # primary_directory = '/home/user_name/open-kbp'  # directory where everything is stored
    primary_directory = '/Users/aaronbabier/Downloads/public_dat-2'
    # Define directory where given data is stored
    training_data_dir = '{}/train-pats'.format(primary_directory)
    validation_data_dir = '{}/validation-pats-no-dose'.format(primary_directory)
    # path where any data generated by this code (e.g., predictions, models) are stored
    results_dir = '{}/results'.format(primary_directory)
    # Name model to train and number of epochs to train it for
    prediction_name = 'baseline'
    number_of_training_epochs = 1

    # Prepare the data directory
    plan_paths = get_paths(training_data_dir, ext='')  # gets the path of each plan's directory
    num_train_pats = np.minimum(50, len(plan_paths))  # number of plans that will be used to train model
    training_paths = plan_paths[:num_train_pats]  # list of training plans
    hold_out_paths = plan_paths[num_train_pats:]  # list of paths used for held out testing

    # Train a model
    data_loader_train = DataLoader(training_paths)
    dose_prediction_model_train = PredictionModel(data_loader_train, results_dir, model_name=prediction_name)
    dose_prediction_model_train.train_model(epochs=number_of_training_epochs, save_frequency=1, keep_model_history=1)

    # Predict dose for the held out set
    data_loader_hold_out = DataLoader(hold_out_paths, mode_name='dose_prediction')
    dose_prediction_model_hold_out = PredictionModel(data_loader_hold_out, results_dir,
                                                     model_name=prediction_name, stage='hold-out')
    dose_prediction_model_hold_out.predict_dose(epoch=number_of_training_epochs)

    # Evaluate dose metrics
    data_loader_hold_out_eval = DataLoader(hold_out_paths, mode_name='evaluation')  # Set data loader
    prediction_paths = get_paths(dose_prediction_model_hold_out.prediction_dir, ext='csv')
    hold_out_prediction_loader = DataLoader(prediction_paths, mode_name='predicted_dose')  # Set prediction loader
    dose_evaluator = EvaluateDose(data_loader_hold_out_eval, hold_out_prediction_loader)

    # print out scores if data was left for a hold out set
    if not data_loader_hold_out_eval.file_paths_list:
        print('No patient information was given to calculate metrics')
    else:
        dvh_score, dose_score = dose_evaluator.make_metrics()
        print('For this out-of-sample test:\n'
              '\tthe DVH score is {:.3f}\n '
              '\tthe dose score is {:.3f}'.format(dvh_score, dose_score))

    # Apply model to validation set
    validation_data_paths = get_paths(validation_data_dir, ext='')  # gets the path of each plan's directory
    validation_data_loader = DataLoader(validation_data_paths, mode_name='dose_prediction')
    dose_prediction_model_validation = PredictionModel(validation_data_loader, results_dir,
                                                       model_name=prediction_name, stage='validation')
    dose_prediction_model_validation.predict_dose(epoch=number_of_training_epochs)

    # Evaluate plans based on dose metrics (no baseline available to compare to)
    validation_eval_data_loader = DataLoader(validation_data_paths, mode_name='dose_prediction')  # Set data loader
    dose_evaluator = EvaluateDose(validation_eval_data_loader)
    dose_evaluator.make_metrics()
    validation_prediction_metrics = dose_evaluator.reference_dose_metric_df.head()

    # Zip dose to submit
    submission_dir = make_directory_and_return_path('{}/submissions'.format(results_dir))
    shutil.make_archive('{}/{}'.format(submission_dir, prediction_name), 'zip', dose_prediction_model_validation.prediction_dir)
