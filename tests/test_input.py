# License: BSD 3 clause
"""
Tests for SKLL inputs, mainly configuration files.

:author: Michael Heilman (mheilman@ets.org)
:author: Nitin Madnani (nmadnani@ets.org)
:author: Dan Blanchard (dblanchard@ets.org)
:author: Aoife Cahill (acahill@ets.org)
"""

import re
import tempfile
from glob import glob
from itertools import product
from os.path import exists, join, normcase, normpath
from pathlib import Path
from shutil import rmtree

import numpy as np
from nose.tools import eq_, ok_, raises

from skll.config import load_cv_folds, locate_file, parse_config_file
from skll.data.readers import safe_float
from skll.experiments import load_featureset
from skll.utils.logging import close_and_remove_logger_handlers, get_skll_logger
from tests import _my_dir, config_dir, other_dir, output_dir, test_dir, train_dir
from tests.utils import (
    create_jsonlines_feature_files,
    fill_in_config_options,
    remove_jsonlines_feature_files,
    unlink,
)


def setup():
    """
    Create necessary directories for testing.
    """
    for dir_path in [train_dir, test_dir, output_dir]:
        Path(dir_path).mkdir(exist_ok=True)

    # create jsonlines feature files
    create_jsonlines_feature_files(train_dir)


def tearDown():
    """
    Clean up after tests.
    """

    # We need to first ensure that all logger file handlers are closed
    # before trying to unlink any of the log files. Otherwise, the
    # tearDown fixture will not work on Windows.
    logger = get_skll_logger('experiment')
    close_and_remove_logger_handlers(logger)

    for path in (glob(join(config_dir, 'test_config_parsing_*.cfg')) +
                 glob(join(config_dir, 'test_relative_paths_auto_dir*.cfg')) +
                 glob(join(output_dir, 'config_parsing*.log')) +
                 [join(config_dir, "test_relative_paths_relative_paths.cfg")]):
        unlink(path)

    for auto_dir in glob(join(output_dir, 'auto*')):
        rmtree(auto_dir)

    remove_jsonlines_feature_files(train_dir)


def check_safe_float_conversion(converted_val, expected_val):
    """
    Check that value and type of converted_val and expected_val are equal.
    """
    eq_(converted_val, expected_val)
    eq_(type(converted_val), type(expected_val))


def test_safe_float_conversion():
    for input_val, expected_val in zip(['1.234', 1.234, '3.0', '3', 3, 'foo'],
                                       [1.234, 1.234, 3.0, 3, 3, 'foo']):
        yield check_safe_float_conversion, safe_float(input_val), expected_val


def test_locate_file_valid_paths1():
    """
    Test that `config.locate_file` works with absolute paths.
    """

    config_abs_path = join(config_dir,
                           'test_config_parsing_relative_path1.cfg')
    open(config_abs_path, 'w').close()
    eq_(locate_file(config_abs_path, _my_dir),
        join(config_dir, 'test_config_parsing_relative_path1.cfg'))


def test_locate_file_valid_paths2():
    """
    Test that `config.locate_file` works with relative paths.
    """

    config_abs_path = join(config_dir,
                           'test_config_parsing_relative_path2.cfg')
    config_rel_path = 'configs/test_config_parsing_relative_path2.cfg'
    open(config_abs_path, 'w').close()
    eq_(locate_file(config_rel_path, _my_dir), config_abs_path)


def test_locate_file_valid_paths3():
    """
    Test that `config.locate_file` works with relative/absolute paths.
    """

    config_abs_path = join(config_dir,
                           'test_config_parsing_relative_path3.cfg')
    config_rel_path = 'configs/test_config_parsing_relative_path3.cfg'
    open(config_abs_path, 'w').close()
    eq_(locate_file(config_abs_path, _my_dir),
        locate_file(config_rel_path, _my_dir))


@raises(IOError)
def test_locate_file_invalid_path():
    """
    Test that `config.locate_file` raises error for paths that do not exist
    """

    locate_file(join(test_dir, 'does_not_exist.cfg'), _my_dir)


@raises(ValueError)
def test_input_checking1():
    """
    Test merging featuresets with different number of examples
    """
    suffix = '.jsonlines'
    featureset = ['test_input_2examples_1', 'test_input_3examples_1']
    load_featureset(train_dir, featureset, suffix, quiet=True)


@raises(ValueError)
def test_input_checking2():
    """
    Test joining featuresets that contain the same features for each instance
    """
    suffix = '.jsonlines'
    featureset = ['test_input_3examples_1', 'test_input_3examples_1']
    load_featureset(train_dir, featureset, suffix, quiet=True)


def test_input_checking3():
    """
    Test to ensure that we correctly merge featuresets
    """
    suffix = '.jsonlines'
    featureset = ['test_input_3examples_1', 'test_input_3examples_2']
    examples_tuple = load_featureset(train_dir, featureset, suffix, quiet=True)
    eq_(examples_tuple.features.shape[0], 3)


def test_one_file_load_featureset():
    """
    Test loading a single file with load_featureset
    """
    suffix = '.jsonlines'
    featureset = ['test_input_2examples_1']
    single_file_fs = load_featureset(
        join(train_dir, 'test_input_2examples_1.jsonlines'),
        '',
        '',
        quiet=True
    )
    single_fs = load_featureset(train_dir, featureset, suffix, quiet=True)
    eq_(single_file_fs, single_fs)


@raises(ValueError)
def check_config_parsing_value_error(config_path):
    """
    Assert that calling `_parse_config_file` on `config_path` raises ValueError
    """
    parse_config_file(config_path)


@raises(TypeError)
def check_config_parsing_type_error(config_path):
    """
    Assert that calling `_parse_config_file` on `config_path` raises TypeError
    """
    parse_config_file(config_path)


@raises(KeyError)
def check_config_parsing_key_error(config_path):
    """
    Assert that calling `_parse_config_file` on `config_path` raises KeyError
    """
    parse_config_file(config_path)


@raises(IOError)
def check_config_parsing_file_not_found_error(config_path):
    """
    Assert that calling `_parse_config_file` on `config_path` raises FileNotFoundError
    """
    parse_config_file(config_path)


@raises(IOError)
def test_empty_config_name_raises_file_not_found_error():
    """
    Assert that calling _parse_config_file on an empty string raises IOError
    """
    parse_config_file("")


def test_config_parsing_no_name():
    """
    Test that config parsing raises an error for missing experiment names
    """

    # make a simple config file that has no experiment name
    values_to_fill_dict = {
        'train_directory': train_dir,
        'test_directory': test_dir,
        'task': 'evaluate',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'no_name')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_task():
    """
    Test to ensure config parsing raises error with invalid/missing task
    """

    # make a simple config file that has a bad task
    # but everything else is correct
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir
    }

    for task_value, sub_prefix in zip([None, '', 'procrastinate'],
                                      ['no_task', 'missing_task', 'bad_task']):
        if task_value is not None:
            values_to_fill_dict['task'] = task_value
        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)

        yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_learner():
    """
    Test that config parsing raises error with missing/bad/duplicate learners
    """

    # make a simple config file that has bad learner specifications
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'logs': output_dir,
        'results': output_dir
    }

    for learners_list, sub_prefix in zip([None, '[]', 'LogisticRegression',
                                          "['LogisticRegression', "
                                          "'LogisticRegression']"],
                                         ['no_learner', 'empty_learner',
                                          'not_list_learner',
                                          'duplicate_learner']):
        if learners_list is not None:
            values_to_fill_dict['learners'] = learners_list

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)
        yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_sampler():
    """
    Test to ensure config file parsing raises an error with an invalid sampler
    """

    # make a simple config file that has bad sampling information
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'sampler': 'RFBSampler'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'bad_sampler')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_hashing():
    """
    Test that config parsing raises error with `feature_hasher` but not `hasher_features`
    """

    # make a simple config file that has bad feature hashing information
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'feature_hasher': 'True'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'bad_hashing')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_featuresets():
    """
    Test that config file parsing raises error with badly specified featuresets
    """

    # make a simple config file that has bad feature sets
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir
    }

    for featuresets, sub_prefix in zip([None, '[]', "{'f1', 'f2', 'f3'}",
                                        "[['f1', 'f2'], 'f3', 'f4']"],
                                       ['no_feats', 'empty_feats',
                                        'non_list_feats1', 'non_list_feats2']):
        if featuresets is not None:
            values_to_fill_dict['featuresets'] = featuresets

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)
        yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_featurenames():
    """
    Test that config parsing raises error with badly specified featureset names
    """

    # make a simple config file that has bad feature names
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'learners': "['LogisticRegression']",
        'featuresets': "[['f1', 'f2', 'f3'], ['f4', 'f5', 'f6']]",
        'logs': output_dir,
        'results': output_dir
    }

    for fname, sub_prefix in zip(["['set_a']", "['1', 2]", "set_a", "1"],
                                 ['wrong_num_names', 'wrong_type_names',
                                  'wrong_num_and_type1',
                                  'wrong_num_and_type2']):
        if fname is not None:
            values_to_fill_dict['featureset_names'] = fname

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)

        yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_scaling():
    """
    Test that config parsing raises error with invalid scaling type
    """

    # make a simple config file that has bad scaling information
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'learners': "['LogisticRegression']",
        'featuresets': "[['f1', 'f2', 'f3'], ['f4', 'f5', 'f6']]",
        'logs': output_dir,
        'results': output_dir
    }

    for scaling_type, sub_prefix in zip(["foo", "True", "False"],
                                        ['bad_scaling1', 'bad_scaling2',
                                         'bad_scaling3']):

        values_to_fill_dict['feature_scaling'] = scaling_type

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)

        yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_train():
    """
    Test that config parsing raises error with invalid train path specifications
    """

    # make a simple config file that has a bad train paths
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'test_directory': test_dir,
        'learners': "['LogisticRegression']",
        'featuresets': "[['f1', 'f2', 'f3'], ['f4', 'f5', 'f6']]",
        'logs': output_dir,
        'results': output_dir
    }

    for sub_prefix in ['no_train_path_or_file',
                       'both_train_path_and_file',
                       'nonexistent_train_path',
                       'nonexistent_test_file']:

        if sub_prefix == 'both_train_path_and_file':
            train_fh = tempfile.NamedTemporaryFile(
                suffix='jsonlines',
                prefix=join(other_dir, 'test_config_parsing_')
            )
            values_to_fill_dict['train_file'] = train_fh.name
            values_to_fill_dict['train_directory'] = train_dir

        elif sub_prefix == 'nonexistent_train_path':
            values_to_fill_dict['train_directory'] = join(train_dir, 'foo')

        elif sub_prefix == 'nonexistent_test_file':
            values_to_fill_dict['train_file'] = 'foo.jsonlines'

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)

        yield check_config_parsing_value_error, config_path

        if sub_prefix == 'both_train_path_and_file':
            train_fh.close()


def test_config_parsing_bad_test():
    """
    Test that config parsing raises error with invalid test path specifications
    """

    # make a simple config file that has bad test path
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'learners': "['LogisticRegression']",
        'featuresets': "[['f1', 'f2', 'f3'], ['f4', 'f5', 'f6']]",
        'logs': output_dir,
        'results': output_dir
    }

    for sub_prefix in ['both_test_path_and_file',
                       'nonexistent_test_path',
                       'nonexistent_test_file']:

        if sub_prefix == 'both_test_path_and_file':
            test_fh = tempfile.NamedTemporaryFile(
                suffix='jsonlines',
                prefix=join(other_dir, 'test_config_parsing_')
            )
            values_to_fill_dict['test_file'] = test_fh.name
            values_to_fill_dict['test_directory'] = test_dir

        elif sub_prefix == 'nonexistent_test_path':
            values_to_fill_dict['test_directory'] = join(test_dir, 'foo')

        elif sub_prefix == 'nonexistent_test_file':
            values_to_fill_dict['test_file'] = 'foo.jsonlines'

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)

        yield check_config_parsing_value_error, config_path

        if sub_prefix == 'both_test_path_and_file':
            test_fh.close()


def test_config_parsing_grid_search_but_no_objectives():
    """
    Test that config parsing raises error with grid search but no objectives
    """

    # make a simple config file that has grid search turned on but no objectives
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir}

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'missing_objective')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_objectives():
    """
    Test that config parsing raises error with grid objectives as strings
    """

    # make a simple config file that has a mistyped objective value
    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'objectives': "accuracy"
    }
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'bad_objectives')
    yield check_config_parsing_type_error, config_path


def test_config_parsing_bad_metric():
    """
    Test that config parsing raises error with metrics as strings
    """

    # make a simple config file that has bad metrics
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'metrics': "accuracy"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'bad_metric_as_string')

    yield check_config_parsing_type_error, config_path


def test_config_parsing_log_loss_no_probability():
    """
    Test that config parsing raises error for `log_loss` without probability
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'grid_search': 'true',
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['neg_log_loss']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'log_loss_no_probability')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_roc_auc_no_probability():
    """
    Test that config parsing raises error for `roc_auc` without probability
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'grid_search': 'false',
        'logs': output_dir,
        'results': output_dir,
        'metrics': "['roc_auc']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'roc_auc_no_probability')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_bad_task_paths():
    """
    Test that config parsing raises error with various incorrectly set paths
    """

    # make a simple config file that has a bad task
    # but everything else is correct
    values_to_fill_dict = {'experiment_name': 'config_parsing',
                           'train_directory': train_dir,
                           'learners': "['LogisticRegression']",
                           'featuresets':
                               "[['f1', 'f2', 'f3'], ['f4', 'f5', 'f6']]",
                           'logs': output_dir}

    for sub_prefix in ['predict_no_test', 'evaluate_no_test',
                       'xv_with_test_path', 'train_with_test_path',
                       'xv_with_test_file', 'train_with_test_file',
                       'train_with_results', 'predict_with_results',
                       'train_no_model', 'train_with_predictions',
                       'xv_with_model']:

        if sub_prefix == 'predict_no_test':
            values_to_fill_dict['task'] = 'predict'
            values_to_fill_dict['predictions'] = output_dir

        elif sub_prefix == 'evaluate_no_test':
            values_to_fill_dict['task'] = 'evaluate'
            values_to_fill_dict['results'] = output_dir

        elif sub_prefix == 'xv_with_test_path':
            values_to_fill_dict['task'] = 'cross_validate'
            values_to_fill_dict['results'] = output_dir
            values_to_fill_dict['test_directory'] = test_dir

        elif sub_prefix == 'train_with_test_path':
            values_to_fill_dict['task'] = 'train'
            values_to_fill_dict['models'] = output_dir
            values_to_fill_dict['test_directory'] = test_dir

        elif sub_prefix == 'xv_with_test_file':
            values_to_fill_dict['task'] = 'cross_validate'
            values_to_fill_dict['results'] = output_dir
            test_fh1 = tempfile.NamedTemporaryFile(
                suffix='jsonlines',
                prefix=join(other_dir, 'test_config_parsing_')
            )
            values_to_fill_dict['test_file'] = test_fh1.name

        elif sub_prefix == 'train_with_test_file':
            values_to_fill_dict['task'] = 'train'
            values_to_fill_dict['models'] = output_dir
            test_fh2 = tempfile.NamedTemporaryFile(
                suffix='jsonlines',
                prefix=join(other_dir, 'test_config_parsing_')
            )

            values_to_fill_dict['test_file'] = test_fh2.name

        elif sub_prefix == 'train_with_results':
            values_to_fill_dict['task'] = 'train'
            values_to_fill_dict['models'] = output_dir
            values_to_fill_dict['results'] = output_dir

        elif sub_prefix == 'predict_with_results':
            values_to_fill_dict['task'] = 'predict'
            values_to_fill_dict['test_directory'] = test_dir
            values_to_fill_dict['predictions'] = output_dir
            values_to_fill_dict['results'] = output_dir

        elif sub_prefix == 'train_no_model':
            values_to_fill_dict['task'] = 'train'

        elif sub_prefix == 'train_with_predictions':
            values_to_fill_dict['task'] = 'train'
            values_to_fill_dict['models'] = output_dir
            values_to_fill_dict['predictions'] = output_dir

        elif sub_prefix == 'xv_with_model':
            values_to_fill_dict['task'] = 'cross_validate'
            values_to_fill_dict['results'] = output_dir
            values_to_fill_dict['models'] = output_dir

        config_template_path = join(config_dir,
                                    'test_config_parsing.template.cfg')
        config_path = fill_in_config_options(config_template_path,
                                             values_to_fill_dict,
                                             sub_prefix)

        yield check_config_parsing_value_error, config_path

        if sub_prefix == 'xv_with_test_file':
            test_fh1.close()

        elif sub_prefix == 'train_with_test_file':
            test_fh2.close()


def test_config_parsing_bad_cv_folds():
    """
    Test that config parsing raises error with invalid `cv_folds`
    """

    # make a simple config file that has a bad value for cv_folds
    # but everything else is correct
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'num_cv_folds': 'random',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'bad_cv_folds')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_save_cv_models_no_models_path():
    """
    Test that config parsing raises error with `save_cv_folds` but no output path
    """

    # make a simple config file that has a bad value for cv_folds
    # but everything else is correct
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'save_cv_models': 'True',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'save_cv_folds_true_no_models_path')

    yield check_config_parsing_value_error, config_path


def test_config_parsing_invalid_option():
    """
    Test that config parsing raises error with invalid config options
    """

    # make a simple config file that has an invalid option
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'bad_option': 'whatever',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'invalid_option')

    yield check_config_parsing_key_error, config_path


def test_config_parsing_duplicate_option():
    """
    Test that config parsing raises error with duplicate config options
    """

    # make a simple config file that has a duplicate option
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'duplicate_option': 'value',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'duplicate_option')

    yield check_config_parsing_key_error, config_path


def test_config_parsing_option_in_wrong_section():
    """
    Test that config parsing raises error with option in wrong section
    """

    # make a simple config file that has an option in the wrong section
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'probability': 'true',
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'option_in_wrong_section')

    yield check_config_parsing_key_error, config_path


def test_config_parsing_mislocated_input_path():
    """
    Test that config parsing raises error with mislocated input path
    """

    # make a simple config file that has a mislocated path
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': 'train',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'mislocated_input_file')

    yield check_config_parsing_file_not_found_error, config_path


@raises(ValueError)
def test_config_parsing_mse_throws_exception():
    """
    Test that config parsing raises error with `mean_squared_error`
    """

    # make a simple config file that has an invalid option
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'objectives': "['mean_squared_error']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'mse_to_neg_mse')

    parse_config_file(config_path)


def test_config_parsing_no_grid_objectives_needed_for_learning_curve():
    """
    Test that config parsing works as expected for learning curves without tuning objectives
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'metrics': "['neg_mean_squared_error']",
        'results': output_dir
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'no_objectives_learning_curve')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(do_grid_search, False)
    eq_(grid_objectives, [])
    eq_(output_metrics, ['neg_mean_squared_error'])


def test_config_parsing_relative_input_path():
    """
    Test that config parsing works as expected with relative input directories
    """

    # make a simple config file that has relative paths
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'mislocated_input_file')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    # we need to use normcase here for Azure package builds to pass
    eq_(normcase(normpath(train_path)), normcase(train_dir))


def test_config_parsing_relative_input_paths():
    """
    Test that config parsing works as expected with relative input file paths
    """

    train_file = join(train_dir, 'f0.jsonlines')
    test_file = join(train_dir, 'f1.jsonlines')

    # make a simple config file that has relative paths
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_file': train_file,
        'test_file': test_file,
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_micro']"
    }

    config_template_path = join(config_dir,
                                'test_relative_paths.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'relative_paths')

    parse_config_file(config_path)


def test_config_parsing_automatic_output_directory_creation():
    """
    Test that output directories in config file are automatically created
    """

    train_file = join(train_dir, 'f0.jsonlines')
    test_file = join(train_dir, 'f1.jsonlines')

    # make a simple config file that has new directories that should
    # be automatically created
    new_log_path = join(output_dir, 'autolog')
    new_results_path = join(output_dir, 'autoresults')
    new_models_path = join(output_dir, 'automodels')
    new_predictions_path = join(output_dir, 'autopredictions')

    ok_(not(exists(new_log_path)))
    ok_(not(exists(new_results_path)))
    ok_(not(exists(new_models_path)))
    ok_(not(exists(new_predictions_path)))

    values_to_fill_dict = {
        'experiment_name': 'auto_dir_creation',
        'task': 'evaluate',
        'train_file': train_file,
        'test_file': test_file,
        'learners': "['LogisticRegression']",
        'logs': new_log_path,
        'results': new_results_path,
        'models': new_models_path,
        'predictions': new_predictions_path,
        'objectives': "['f1_score_micro']"
    }

    config_template_path = join(config_dir,
                                'test_relative_paths.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'auto_dir_creation')

    parse_config_file(config_path)

    ok_(exists(new_log_path))
    ok_(exists(new_results_path))
    ok_(exists(new_models_path))
    ok_(exists(new_predictions_path))


def test_cv_folds_and_grid_search_folds():
    """
    Test config parsing for various `cv_folds` and `grid_search_folds` combos
    """

    # we want to test all possible combinations of the following variables:
    #  task = train, evaluate, predict, cross_validate
    #  cv_folds/folds_file = not specified, number, csv file
    #  grid_search_folds = not specified, number
    #  use_folds_file_for_grid_search = not specified, True, False

    # below is a table of what we expect for each of the combinations
    # note: `fold_mapping` refers to the dictionary version of the folds file

    # task, cv_folds/folds_file, grid_search_folds, use_folds_file_for_grid_search -> cv_folds, grid_search_folds
    # ('train', None, None, None) ->  (None, 5)
    # ('train', None, None, True) ->  (None, 5)
    # ('train', None, None, False) ->  (None, 5)
    # ('train', None, 7, None) ->  (None, 7)
    # ('train', None, 7, True) ->  (None, 7)
    # ('train', None, 7, False) ->  (None, 7)
    # ('train', 5, None, None) ->  (None, 5)
    # ('train', 5, None, True) ->  (None, 5)
    # ('train', 5, None, False) ->   (None, 5)
    # ('train', 5, 7, None) ->  (None, 7)
    # ('train', 5, 7, True) ->  (None, 7)
    # ('train', 5, 7, False) ->  (None, 7)
    # ('train', 'train/folds_file_test.csv', None, None) ->  (None, fold_mapping)
    # ('train', 'train/folds_file_test.csv', None, True) ->  (None, fold_mapping)
    # ('train', 'train/folds_file_test.csv', None, False) ->  (None, fold_mapping)
    # ('train', 'train/folds_file_test.csv', 7, None) ->  (None, fold_mapping)
    # ('train', 'train/folds_file_test.csv', 7, True) ->  (None, fold_mapping)
    # ('train', 'train/folds_file_test.csv', 7, False) ->  (None, fold_mapping)
    # ('evaluate', None, None, None) ->  (None, 5)
    # ('evaluate', None, None, True) ->  (None, 5)
    # ('evaluate', None, None, False) ->  (None, 5)
    # ('evaluate', None, 7, None) ->  (None, 7)
    # ('evaluate', None, 7, True) ->  (None, 7)
    # ('evaluate', None, 7, False) ->  (None, 7)
    # ('evaluate', 5, None, None) ->  (None, 5)
    # ('evaluate', 5, None, True) ->  (None, 5)
    # ('evaluate', 5, None, False) ->   (None, 5)
    # ('evaluate', 5, 7, None) ->  (None, 7)
    # ('evaluate', 5, 7, True) ->  (None, 7)
    # ('evaluate', 5, 7, False) ->  (None, 7)
    # ('evaluate', 'train/folds_file_test.csv', None, None) ->  (None, fold_mapping)
    # ('evaluate', 'train/folds_file_test.csv', None, True) ->  (None, fold_mapping)
    # ('evaluate', 'train/folds_file_test.csv', None, False) ->  (None, fold_mapping)
    # ('evaluate', 'train/folds_file_test.csv', 7, None) ->  (None, fold_mapping)
    # ('evaluate', 'train/folds_file_test.csv', 7, True) ->  (None, fold_mapping)
    # ('evaluate', 'train/folds_file_test.csv', 7, False) ->  (None, fold_mapping)
    # ('predict', None, None, None) ->  (None, 5)
    # ('predict', None, None, True) ->  (None, 5)
    # ('predict', None, None, False) ->  (None, 5)
    # ('predict', None, 7, None) ->  (None, 7)
    # ('predict', None, 7, True) ->  (None, 7)
    # ('predict', None, 7, False) ->  (None, 7)
    # ('predict', 5, None, None) ->  (None, 5)
    # ('predict', 5, None, True) ->  (None, 5)
    # ('predict', 5, None, False) ->   (None, 5)
    # ('predict', 5, 7, None) ->  (None, 7)
    # ('predict', 5, 7, True) ->  (None, 7)
    # ('predict', 5, 7, False) ->  (None, 7)
    # ('predict', 'train/folds_file_test.csv', None, None) ->  (None, fold_mapping)
    # ('predict', 'train/folds_file_test.csv', None, True) ->  (None, fold_mapping)
    # ('predict', 'train/folds_file_test.csv', None, False) ->  (None, fold_mapping)
    # ('predict', 'train/folds_file_test.csv', 7, None) ->  (None, fold_mapping)
    # ('predict', 'train/folds_file_test.csv', 7, True) ->  (None, fold_mapping)
    # ('predict', 'train/folds_file_test.csv', 7, False) ->  (None, fold_mapping)
    # ('cross_validate', None, None, None) ->  (10, 5)
    # ('cross_validate', None, None, True) ->  (10, 5)
    # ('cross_validate', None, None, False) ->  (10, 5)
    # ('cross_validate', None, 7, None) ->  (10, 7)
    # ('cross_validate', None, 7, True) ->  (10, 7)
    # ('cross_validate', None, 7, False) ->  (10, 7)
    # ('cross_validate', 5, None, None) ->  (5, 5)
    # ('cross_validate', 5, None, True) ->  (5, 5)
    # ('cross_validate', 5, None, False) ->  (5, 5)
    # ('cross_validate', 5, 7, None) ->  (5, 7)
    # ('cross_validate', 5, 7, True) ->  (5, 7)
    # ('cross_validate', 5, 7, False) ->  (5, 7)
    # ('cross_validate', 'train/folds_file_test.csv', None, None) ->  (fold_mapping, fold_mapping)
    # ('cross_validate', 'train/folds_file_test.csv', None, True) ->  (fold_mapping, fold_mapping)
    # ('cross_validate', 'train/folds_file_test.csv', None, False) ->  (fold_mapping, 5)
    # ('cross_validate', 'train/folds_file_test.csv', 7, None) ->  (fold_mapping, fold_mapping)
    # ('cross_validate', 'train/folds_file_test.csv', 7, True) ->  (fold_mapping, fold_mapping)
    # ('cross_validate', 'train/folds_file_test.csv', 7, False) ->  (fold_mapping, 7)

    # note that we are passing the string 'fold_mapping' instead of passing in the
    # actual fold mapping dictionary since we don't want it printed in the test log

    for ((task,
          cv_folds_or_file,
          grid_search_folds,
          use_folds_file_for_grid_search),
         (chosen_cv_folds,
          chosen_grid_search_folds)) in zip(product(['train', 'evaluate', 'predict', 'cross_validate'],
                                                    [None, 5, join(train_dir, 'folds_file_test.csv')],
                                                    [None, 7],
                                                    [None, True, False]),
                                            [(None, 5), (None, 5), (None, 5),
                                             (None, 7), (None, 7), (None, 7),
                                             (None, 5), (None, 5), (None, 5),
                                             (None, 7), (None, 7), (None, 7),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 5), (None, 5), (None, 5),
                                             (None, 7), (None, 7), (None, 7),
                                             (None, 5), (None, 5), (None, 5),
                                             (None, 7), (None, 7), (None, 7),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 5), (None, 5), (None, 5),
                                             (None, 7), (None, 7), (None, 7),
                                             (None, 5), (None, 5), (None, 5),
                                             (None, 7), (None, 7), (None, 7),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (None, 'fold_mapping'), (None, 'fold_mapping'),
                                             (10, 5), (10, 5), (10, 5), (10, 7),
                                             (10, 7), (10, 7), (5, 5), (5, 5),
                                             (5, 5), (5, 7), (5, 7), (5, 7),
                                             ('fold_mapping', 'fold_mapping'),
                                             ('fold_mapping', 'fold_mapping'),
                                             ('fold_mapping', 5),
                                             ('fold_mapping', 'fold_mapping'),
                                             ('fold_mapping', 'fold_mapping'),
                                             ('fold_mapping', 7)]):

        yield (check_cv_folds_and_grid_search_folds, task, cv_folds_or_file,
               grid_search_folds, use_folds_file_for_grid_search,
               chosen_cv_folds, chosen_grid_search_folds)


def check_cv_folds_and_grid_search_folds(task,
                                         cv_folds_or_file,
                                         grid_search_folds,
                                         use_folds_file_for_grid_search,
                                         chosen_cv_folds,
                                         chosen_grid_search_folds):

    # read in the folds file into a dictionary and replace the string
    # 'fold_mapping' with this dictionary.
    fold_mapping = load_cv_folds(join(train_dir, 'folds_file_test.csv'),
                                 ids_to_floats=False)
    if chosen_grid_search_folds == 'fold_mapping':
        chosen_grid_search_folds = fold_mapping
    if chosen_cv_folds == 'fold_mapping':
        chosen_cv_folds = fold_mapping

    # make a simple config file
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': task,
        'grid_search': 'true',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'objectives': "['f1_score_macro']"
    }

    # we need the models field when training but the results field
    # when cross-validating
    if task == 'train':
        values_to_fill_dict['models'] = output_dir
    elif task in ['evaluate', 'predict']:
        values_to_fill_dict['test_directory'] = test_dir
    elif task == 'cross_validate':
        values_to_fill_dict['results'] = output_dir

    # now add the various fields that are passed in
    if isinstance(cv_folds_or_file, int):
        values_to_fill_dict['num_cv_folds'] = str(cv_folds_or_file)
    elif isinstance(cv_folds_or_file, str):
        values_to_fill_dict['folds_file'] = cv_folds_or_file

    if isinstance(grid_search_folds, int):
        values_to_fill_dict['grid_search_folds'] = str(grid_search_folds)

    if isinstance(use_folds_file_for_grid_search, bool):
        values_to_fill_dict['use_folds_file_for_grid_search'] = str(use_folds_file_for_grid_search).lower()

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'test_cv_and_grid_search_folds')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(cv_folds, chosen_cv_folds)
    eq_(grid_search_folds, chosen_grid_search_folds)


def test_default_number_of_cv_folds():
    """
    Test that config parsing works as expected without `cv_folds` being set
    """

    # make a simple config file that does not set `cv_folds`

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'grid_search': 'true',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_cv_folds')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(cv_folds, 10)


def test_setting_number_of_cv_folds():
    """
    Test that config parsing works as expected with `cv_folds` explicitly set
    """

    # make a simple config file that explicitly sets `cv_folds`
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'num_cv_folds': "5",
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_cv_folds')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(cv_folds, 5)


def test_default_cv_seed():
    """
    Test that config parsing works as expected with the default `cv_seed`
    """

    # make a simple config file that does not set `cv_seed`

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'train_directory': train_dir,
        'grid_search': 'true',
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_cv_folds')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(cv_seed, 123456789)


def test_setting_cv_seed():
    """
    Test that config parsing works as expected with `cv_seed` explicitly set
    """

    # make a simple config file that explicitly sets `cv_seed`
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'cross_validate',
        'cv_seed': "987",
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'num_cv_folds': "5",
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_cv_folds')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(cv_seed, 987)


def test_setting_param_grids():
    """
    Test that config parsing works as expected with specified param grids
    """

    # make a simple config file that does not set cv_folds

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LinearSVC']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'param_grids': "[{'C': [1e-6, 0.001, 1, 10, 100, 1e5]}]",
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'param_grids')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(param_grid_list[0]['C'][0], 1e-6)
    eq_(param_grid_list[0]['C'][1], 1e-3)
    eq_(param_grid_list[0]['C'][2], 1)
    eq_(param_grid_list[0]['C'][3], 10)
    eq_(param_grid_list[0]['C'][4], 100)
    eq_(param_grid_list[0]['C'][5], 1e5)


def test_setting_fixed_parameters():
    """
    Test that config parsing works as expected with specified fixed parameters
    """

    # make a simple config file that does not set cv_folds

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LinearSVC']",
        'logs': output_dir,
        'results': output_dir,
        'fixed_parameters': "[{'C': [1e-6, 0.001, 1, 10, 100, 1e5]}]",
        'grid_search': 'true',
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'fixed_parameters')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(fixed_parameter_list[0]['C'][0], 1e-6)
    eq_(fixed_parameter_list[0]['C'][1], 1e-3)
    eq_(fixed_parameter_list[0]['C'][2], 1)
    eq_(fixed_parameter_list[0]['C'][3], 10)
    eq_(fixed_parameter_list[0]['C'][4], 100)
    eq_(fixed_parameter_list[0]['C'][5], 1e5)


@raises(ValueError)
def test_learning_curve_objectives_unsupported_error():
    """
    Test that config parsing raises error for `objectives` with learning curves
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'objectives': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_learning_curve')

    parse_config_file(config_path)


def test_default_learning_curve_options():
    """
    Test that config parsing works as expected with default learning curve options
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'grid_search': 'true',
        'metrics': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_learning_curve')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(learning_curve_cv_folds_list, [10, 10])
    ok_(np.all(learning_curve_train_sizes == np.linspace(0.1, 1.0, 5)))


def test_setting_learning_curve_options():
    """
    Test that config parsing works as expected with specified learning curve options
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'learning_curve_cv_folds_list': "[100, 10]",
        'learning_curve_train_sizes': "[10, 50, 100, 200, 500]",
        'metrics': "['f1_score_macro']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'setting_learning_curve')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(learning_curve_cv_folds_list, [100, 10])
    eq_(learning_curve_train_sizes, [10, 50, 100, 200, 500])


@raises(ValueError)
def test_learning_curve_metrics_and_objectives_throw_error():
    """
    Test that config parsing raises error for learning curve `metrics` and `objectives`
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': "['f1_score_macro']",
        'metrics': '["accuracy", "f1_score_micro"]'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_metrics_and_objectives'
    )

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(output_metrics, ["accuracy", "f1_score_micro"])


def test_learning_curve_metrics_and_no_objectives():
    """
    Test that config parsing works for learning curves with `metrics` but no `objectives`
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'metrics': '["accuracy", "unweighted_kappa"]'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_metrics_and_no_objectives'
    )

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(output_metrics, ["accuracy", "unweighted_kappa"])


def test_learning_curve_metrics():
    """
    Test that config parsing works for learning curves with `metrics` only
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'metrics': '["accuracy"]'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_objectives_and_no_metrics'
    )

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(output_metrics, ["accuracy"])
    eq_(grid_objectives, [])


def test_learning_curve_pipeline_option():
    """
    Test that config parsing works for learning curves with `pipeline` set
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'pipeline': 'true',
        'metrics': '["accuracy", "unweighted_kappa"]'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_metrics_and_no_objectives'
    )

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(pipeline, True)


def test_learning_curve_no_metrics():
    """
    Test that config parsing works for learning curves with no `metrics`
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_default_objectives_and_no_metrics'
    )

    yield check_config_parsing_value_error, config_path


def test_learning_curve_no_metrics_and_no_objectives():
    """
    Test that config parsing works for learning curves with no `metrics` or `objectives`
    """
    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'logs': output_dir,
        'results': output_dir,
        'objectives': '[]'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_no_metrics_and_no_objectives'
    )

    yield check_config_parsing_value_error, config_path


def test_learning_curve_bad_folds_specifications():
    """
    Test that config parsing raises error for bad learning curve folds
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'learning_curve',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learning_curve_cv_folds_list': "[10]",
        'learners': "['LogisticRegression', 'MultinomialNB']",
        'metrics': "['accuracy', 'f1_score_macro']",
        'logs': output_dir,
        'results': output_dir
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(
        config_template_path,
        values_to_fill_dict,
        'learning_curve_bad_folds_specifications'
    )
    yield check_config_parsing_value_error, config_path


def test_config_parsing_param_grids_no_grid_search():
    """
    Test that config parsing raises warning for no grid search with param grids
    """

    # make a simple config file that turns off grid search but specifies param grids
    values_to_fill_dict = {
        'experiment_name': 'config_parsing_param_grids_no_grid_search',
        'task': 'train',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LinearSVC']",
        'logs': output_dir,
        'models': output_dir,
        'grid_search': 'false',
        'param_grids': "[{'C': [1e-6, 0.001, 1, 10, 100, 1e5]}]"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'param_grids_no_grid_search')

    parse_config_file(config_path)
    log_path = join(output_dir,
                    "config_parsing_param_grids_no_grid_search.log")
    with open(log_path) as f:
        warning_pattern = re.compile(
            r'Since "grid_search" is set to False, the specified '
            r'"param_grids" will be ignored.'
        )
        matches = re.findall(warning_pattern, f.read())
        eq_(len(matches), 1)


def test_config_parsing_no_grid_search_but_objectives_specified():
    """
    Test that config parsing raises warning if no grid search with `objectives`
    """

    # make a simple config file that has grid search off but still specifies objectives
    values_to_fill_dict = {
        'experiment_name': 'config_parsing_objectives_no_grid_search',
        'task': 'train',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LinearSVC']",
        'logs': output_dir,
        'models': output_dir,
        'grid_search': 'false',
        'objectives': "['f1_score_macro', 'accuracy']"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'objectives_no_grid_search')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(do_grid_search, False)
    eq_(grid_objectives, [])

    log_path = join(output_dir, "config_parsing_objectives_no_grid_search.log")
    with open(log_path) as f:
        warning_pattern = re.compile(
            r'Since "grid_search" is set to False, any specified "objectives"'
            r' will be ignored.'
        )
        matches = re.findall(warning_pattern, f.read())
        eq_(len(matches), 1)


def test_config_parsing_param_grids_fixed_parameters_conflict():
    """
    Test that config parsing raises warning for both param grids and fixed params
    """

    # make a simple config file that has a bad task
    # but everything else is correct
    values_to_fill_dict = {
        'experiment_name':
            'config_parsing_param_grids_fixed_parameters_conflict',
        'task': 'train',
        'train_directory': train_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LinearSVC']",
        'logs': output_dir,
        'models': output_dir,
        'grid_search': 'true',
        'objectives': "['f1_score_macro']",
        'fixed_parameters': "[{'C': 0.001}]",
        'param_grids': "[{'C': [1e-6, 0.001, 1, 10, 100, 1e5]}]"
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')
    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'param_grids_no_grid_search')

    parse_config_file(config_path)
    log_path = join(output_dir,
                    "config_parsing_param_grids_fixed_parameters_conflict.log")
    with open(log_path) as f:
        warning_pattern = re.compile(
            r'Note that "grid_search" is set to True and "fixed_parameters" '
            r'is also specified. If there is a conflict between the grid '
            r'search parameter space and the fixed parameter values, the '
            r'fixed parameter values will take precedence.'
        )
        matches = re.findall(warning_pattern, f.read())
        eq_(len(matches), 1)


def test_config_parsing_default_pos_label_value():
    """
    Test that config parsing works with default `pos_label` value
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'objectives': "['accuracy']",
        'logs': output_dir,
        'results': output_dir
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_value_pos_label')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(pos_label, None)


def test_config_parsing_default_save_votes_value():
    """
    Test that config parsing works as expected for default `save_votes` value
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'fixed_parameters': '[{"estimator_names": ["SVC", "LogisticRegression", "MultinomialNB"]}]',
        'learners': "['VotingClassifier']",
        'objectives': "['accuracy']",
        'logs': output_dir,
        'results': output_dir,
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'default_value_save_votes')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(save_votes, False)


def test_config_parsing_set_save_votes_value():
    """
    Test that config parsing works as expected for specified `save_votes` value
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'fixed_parameters': '[{"estimator_names": ["SVC", "LogisticRegression", "MultinomialNB"]}]',
        'learners': "['VotingClassifier']",
        'objectives': "['accuracy']",
        'logs': output_dir,
        'results': output_dir,
        'save_votes': 'true'
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'set_value_save_votes')

    (experiment_name, task, sampler, fixed_sampler_parameters,
     feature_hasher, hasher_features, id_col, label_col, train_set_name,
     test_set_name, suffix, featuresets, do_shuffle, model_path,
     do_grid_search, grid_objectives, probability, pipeline, results_path,
     pos_label, feature_scaling, min_feature_count, folds_file,
     grid_search_jobs, grid_search_folds, cv_folds, cv_seed, save_cv_folds,
     save_cv_models, use_folds_file_for_grid_search, do_stratified_folds,
     fixed_parameter_list, param_grid_list, featureset_names, learners,
     prediction_dir, log_path, train_path, test_path, ids_to_floats,
     class_map, custom_learner_path, custom_metric_path, learning_curve_cv_folds_list,
     learning_curve_train_sizes, output_metrics, save_votes) = parse_config_file(config_path)

    eq_(save_votes, True)


@raises(KeyError)
def test_config_parsing_use_log_instead_of_logs():
    """
    Test that config parsing raises error for `log` option instead of `logs`
    """

    values_to_fill_dict = {
        'experiment_name': 'config_parsing_log_vs_logs',
        'task': 'evaluate',
        'train_directory': train_dir,
        'test_directory': test_dir,
        'featuresets': "[['f1', 'f2', 'f3']]",
        'learners': "['LogisticRegression']",
        'objectives': "['accuracy']",
        'log': output_dir,
        'results': output_dir
    }

    config_template_path = join(config_dir,
                                'test_config_parsing.template.cfg')

    config_path = fill_in_config_options(config_template_path,
                                         values_to_fill_dict,
                                         'use_log_vs_logs')

    parse_config_file(config_path)
