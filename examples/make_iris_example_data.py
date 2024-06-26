#!/usr/bin/env python

"""
This is a simple script to download and transform some example data from
sklearn.datasets.

:author: Michael Heilman (mheilman@ets.org)
:organization: ETS
"""

import json
import os
import sys

import sklearn.datasets
from sklearn.model_selection import train_test_split


def main():
    """
    Download some example data and split it into training and test data.
    """
    print('Retrieving iris data from servers...', end='')
    iris_data = sklearn.datasets.load_iris()
    print('done')
    sys.stdout.flush()

    X = iris_data['data']
    Y = [iris_data['target_names'][label] for label in iris_data['target']]

    examples = [{'id': f'EXAMPLE_{i}',
                 'y': y,
                 'x': {f'f{j}': x_val for j, x_val in enumerate(x)}}
                for i, (x, y) in enumerate(zip(X, Y))]

    examples_train, examples_test = train_test_split(examples, test_size=0.33,
                                                     random_state=42)

    print('Writing training and testing files...', end='')
    for examples, suffix in [(examples_train, 'train'), (examples_test,
                                                         'test')]:
        iris_dir = os.path.join('iris', suffix)
        if not os.path.exists(iris_dir):
            os.makedirs(iris_dir)
        jsonlines_path = os.path.join(iris_dir,
                                      'example_iris_features.jsonlines')
        with open(jsonlines_path, 'w') as f:
            for ex in examples:
                f.write(f'{json.dumps(ex)}\n')
    print('done')


if __name__ == '__main__':
    main()
