from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.ml import bp
from app.models.ml_model import MLModel
from app.models.spreadsheet import Spreadsheet
import json
import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score
from sklearn.preprocessing import LabelEncoder

@bp.route('/create', methods=['POST'])
@login_required
def create():
    # Get form data
    spreadsheet_id = request.form.get('spreadsheet_id')
    name = request.form.get('model_name', '').strip()
    model_type = request.form.get('model_type')
    input_columns = request.form.getlist('input_columns')
    output_column = request.form.get('output_column')
    
    # Validate input
    if not name or not model_type or not input_columns or not output_column or not spreadsheet_id:
        return jsonify({
            'success': False, 
            'message': 'Missing required fields'
        })
    
    # Verify that spreadsheet exists and belongs to user
    spreadsheet = Spreadsheet.query.get_or_404(spreadsheet_id)
    if spreadsheet.user_id != current_user.id:
        return jsonify({
            'success': False, 
            'message': 'Unauthorized access to spreadsheet'
        })
    
    # Load spreadsheet data
    try:
        data = json.loads(spreadsheet.data)
    except:
        data = {}
    
    # Create model
    model = MLModel(
        name=name,
        model_type=model_type,
        input_columns=json.dumps(input_columns),
        output_column=output_column,
        spreadsheet_id=spreadsheet_id
    )
    
    # Train the model
    try:
        X, y, metrics = train_model(data, input_columns, output_column, model_type)
        model.metrics = json.dumps(metrics)
        db.session.add(model)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Model {name} created successfully',
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error training model: {str(e)}'
        })

def train_model(data, input_cols, output_col, model_type):
    """Train a model with the given data and parameters"""
    # Prepare the data
    X = []
    y = []
    
    # Get all row indices from the data
    rows = set()
    for key in data.keys():
        if '-' in key:
            row, _ = key.split('-')
            rows.add(int(row))
    
    # Convert column letters to indices
    input_indices = [ord(col) - 65 for col in input_cols]  # A=0, B=1, etc.
    output_index = ord(output_col) - 65
    
    # For each row, get the input and output values
    for row in rows:
        row_inputs = []
        for col_idx in input_indices:
            cell_key = f"{row}-{col_idx}"
            if cell_key in data and data[cell_key]:
                # Try to convert to float, handle errors
                try:
                    row_inputs.append(float(data[cell_key]))
                except ValueError:
                    row_inputs.append(0)  # Default to 0 for non-numeric values
            else:
                row_inputs.append(0)  # Default for missing data
        
        # Skip rows with missing output
        output_key = f"{row}-{output_index}"
        if output_key not in data or not data[output_key]:
            continue
        
        try:
            X.append(row_inputs)
            y_val = data[output_key]
            if model_type == "regression":
                y.append(float(y_val))
            else:
                y.append(y_val)  # Keep string labels for classification
        except ValueError:
            # Skip rows with non-numeric output for regression
            if model_type == "regression":
                continue
            y.append(y_val)  # Keep string labels for classification
    
    # Check if we have enough data
    if len(X) < 2:
        raise ValueError("Not enough data for training")
    
    # Convert to numpy arrays
    X = np.array(X)
    y = np.array(y)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train model
    if model_type == 'regression':
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        metrics = {
            'mse': float(mean_squared_error(y_test, y_pred)),
            'r2': float(r2_score(y_test, y_pred)),
            'coef': model.coef_.tolist(),
            'intercept': float(model.intercept_)
        }
    else:  # classification
        # Use LabelEncoder to convert string labels to numeric
        label_encoder = LabelEncoder()
        y_train_encoded = label_encoder.fit_transform(y_train)
        y_test_encoded = label_encoder.transform(y_test)
        
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train, y_train_encoded)
        
        # Evaluate
        y_pred = model.predict(X_test)
        metrics = {
            'accuracy': float(accuracy_score(y_test_encoded, y_pred)),
            'coef': model.coef_.tolist(),
            'intercept': model.intercept_.tolist(),
            'classes': label_encoder.classes_.tolist()  # Store the mapping of numeric to string labels
        }
    
    return X, y, metrics

@bp.route('/list/<int:spreadsheet_id>')
@login_required
def list_models(spreadsheet_id):
    # Verify that spreadsheet exists and belongs to user
    spreadsheet = Spreadsheet.query.get_or_404(spreadsheet_id)
    if spreadsheet.user_id != current_user.id:
        return jsonify({
            'success': False, 
            'message': 'Unauthorized access to spreadsheet'
        })
    
    # Get all models for this user through their spreadsheets
    models = MLModel.query.join(Spreadsheet).filter(Spreadsheet.user_id == current_user.id).all()
    model_list = []
    
    for model in models:
        # Get the source spreadsheet's column names and types
        source_spreadsheet = Spreadsheet.query.get(model.spreadsheet_id)
        try:
            source_column_names = json.loads(source_spreadsheet.column_names)
        except:
            source_column_names = {}
            
        try:
            source_data = json.loads(source_spreadsheet.data)
            source_column_types = {}
            for col_letter in [chr(i) for i in range(65, 75)]:  # A through J
                col_type = detect_column_type(source_data, col_letter)
                if col_type:
                    source_column_types[col_letter] = col_type
        except:
            source_column_types = {}
        
        model_data = {
            'id': model.id,
            'name': model.name,
            'type': model.model_type,
            'created_at': model.created_at.strftime('%Y-%m-%d %H:%M'),
            'input_columns': json.loads(model.input_columns),
            'output_column': model.output_column,
            'source_spreadsheet': {
                'id': model.spreadsheet_id,
                'name': source_spreadsheet.name
            },
            'source_column_names': source_column_names,
            'source_column_types': source_column_types
        }
        
        # Add metrics if available
        try:
            model_data['metrics'] = json.loads(model.metrics)
        except:
            model_data['metrics'] = {}
            
        model_list.append(model_data)
    
    return jsonify({
        'success': True,
        'models': model_list
    })

@bp.route('/evaluate/<int:model_id>', methods=['POST'])
@login_required
def evaluate(model_id):
    """Evaluate a model with the given input values"""
    # Get the model
    model = MLModel.query.get_or_404(model_id)
    
    # Check if user has access to this model
    spreadsheet = Spreadsheet.query.get(model.spreadsheet_id)
    if not spreadsheet or spreadsheet.user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to use this model'
        })
    
    # Get input values from request
    try:
        input_values = request.json.get('inputs', [])
        if not input_values or not isinstance(input_values, list):
            raise ValueError("Invalid input format")
    except:
        return jsonify({
            'success': False,
            'message': 'Invalid input data'
        })
    
    # Get model parameters
    try:
        metrics = json.loads(model.metrics)
        input_columns = json.loads(model.input_columns)
        
        # Check if number of inputs matches expected
        if len(input_values) != len(input_columns):
            return jsonify({
                'success': False,
                'message': f'Expected {len(input_columns)} inputs, got {len(input_values)}'
            })
        
        # Convert all inputs to float
        input_values = [float(val) if val else 0 for val in input_values]
        
        # Apply the model
        if model.model_type == 'regression':
            # For regression, apply linear formula: y = b0 + b1*x1 + b2*x2 + ...
            coef = metrics.get('coef', [])
            intercept = metrics.get('intercept', 0)
            result = intercept
            
            for i, val in enumerate(input_values):
                if i < len(coef):
                    result += coef[i] * val
        else:
            # For classification, calculate probabilities for each class
            coef = metrics.get('coef', [])
            intercepts = metrics.get('intercept', [])
            classes = metrics.get('classes', [])
            
            if not coef or not intercepts or not classes:
                raise ValueError("Missing model parameters for classification")
            
            # For binary classification, we only have one set of coefficients
            if len(classes) == 2:
                # Calculate log-odds for the positive class
                log_odds = intercepts[0]
                for i, val in enumerate(input_values):
                    if i < len(coef[0]):
                        log_odds += coef[0][i] * val
                
                # Convert to probability using sigmoid
                probability = 1 / (1 + np.exp(-log_odds))
                
                # Get the predicted class
                predicted_class_index = 1 if probability > 0.5 else 0
                result = classes[predicted_class_index]
            else:
                # For multi-class classification
                # Calculate log-odds for each class
                log_odds = []
                for i in range(len(classes)):
                    log_odds_i = intercepts[i]
                    for j, val in enumerate(input_values):
                        if j < len(coef[i]):
                            log_odds_i += coef[i][j] * val
                    log_odds.append(log_odds_i)
                
                # Convert log-odds to probabilities using softmax
                exp_log_odds = np.exp(log_odds)
                probabilities = exp_log_odds / np.sum(exp_log_odds)
                
                # Get the class with highest probability
                predicted_class_index = np.argmax(probabilities)
                result = classes[predicted_class_index]
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error evaluating model: {str(e)}'
        }) 