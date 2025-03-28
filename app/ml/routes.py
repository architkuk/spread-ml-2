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
                y.append(y_val)
        except ValueError:
            # Skip rows with non-numeric output
            continue
    
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
        # Convert to binary for demo purposes
        y_train_binary = (y_train > np.median(y_train)).astype(int)
        y_test_binary = (y_test > np.median(y_test)).astype(int)
        
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train, y_train_binary)
        
        # Evaluate
        y_pred = model.predict(X_test)
        metrics = {
            'accuracy': float(accuracy_score(y_test_binary, y_pred)),
            'coef': model.coef_.tolist(),
            'intercept': float(model.intercept_[0])
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
    
    # Get models for this spreadsheet
    models = MLModel.query.filter_by(spreadsheet_id=spreadsheet_id).all()
    model_list = []
    
    for model in models:
        model_data = {
            'id': model.id,
            'name': model.name,
            'type': model.model_type,
            'created_at': model.created_at.strftime('%Y-%m-%d %H:%M'),
            'input_columns': json.loads(model.input_columns),
            'output_column': model.output_column
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
            # For classification, apply logistic regression
            coef = metrics.get('coef', [])[0] if metrics.get('coef') else []
            intercept = metrics.get('intercept', 0)
            # Calculate log-odds
            log_odds = intercept
            for i, val in enumerate(input_values):
                if i < len(coef):
                    log_odds += coef[i] * val
            
            # Convert to probability using sigmoid function
            import math
            probability = 1 / (1 + math.exp(-log_odds))
            # Classification result (0 or 1)
            result = 1 if probability > 0.5 else 0
        
        return jsonify({
            'success': True,
            'result': float(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error evaluating model: {str(e)}'
        }) 