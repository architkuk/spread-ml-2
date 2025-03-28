document.addEventListener('DOMContentLoaded', function () {
    // -------------------------------
    // Global Variables and Element References
    // -------------------------------
    let modelCache = {};
    const spreadsheetEl = document.getElementById('spreadsheet');
    if (!spreadsheetEl) return; // Exit if the spreadsheet element is not present
  
    const spreadsheetId = spreadsheetEl.dataset.id;
    const saveBtn = document.getElementById('save-btn');
    const createModelBtn = document.getElementById('create-model-btn');
    const modelsListEl = document.getElementById('models-list');
    const editorInput = document.getElementById('editor-input');
  
    // Default grid dimensions
    const rows = 100;
    const cols = 10;
  
    // In-memory representation of spreadsheet data
    let spreadsheetData = {};
    let columnNames = {};  // Store custom column names
  
    // Track the currently selected cell
    let selectedCell = null;
    let selectionStart = null;
    let selectionEnd = null;
    let isSelecting = false;
  
    // -------------------------------
    // Load Initial Spreadsheet Data
    // -------------------------------
    if (spreadsheetEl.dataset.initial) {
      try {
        spreadsheetData = JSON.parse(spreadsheetEl.dataset.initial);
      } catch (e) {
        console.error('Error parsing initial spreadsheet data:', e);
      }
    }
  
    // Load column names if available
    if (spreadsheetEl.dataset.columnNames) {
      try {
        columnNames = JSON.parse(spreadsheetEl.dataset.columnNames);
      } catch (e) {
        console.error('Error parsing column names:', e);
      }
    }
  
    // -------------------------------
    // Utility Functions
    // -------------------------------
  
    /**
     * Update the in-memory spreadsheet data.
     * @param {number} row - Row index.
     * @param {number} col - Column index.
     * @param {string} value - New cell value.
     */
    function updateData(row, col, value) {
      const cellKey = `${row}-${col}`;
      if (value) {
        spreadsheetData[cellKey] = value;
      } else {
        delete spreadsheetData[cellKey];
      }
    }
  
    /**
     * Display a temporary message.
     * @param {string} message - The message to display.
     * @param {string} type - The message type ('success' or 'error').
     */
    function showMessage(message, type) {
      const msgEl = document.createElement('div');
      msgEl.className = `message message-${type}`;
      msgEl.textContent = message;
      document.body.appendChild(msgEl);
      setTimeout(() => {
        msgEl.style.opacity = '0';
        setTimeout(() => msgEl.remove(), 300);
      }, 3000);
    }
  
    /**
     * Save spreadsheet data via API call.
     * @param {function} [callback] - Optional callback after saving.
     */
    function saveSpreadsheet(callback) {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';
  
      fetch(`/spreadsheet/save/${spreadsheetId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          data: spreadsheetData,
          column_names: columnNames
        })
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            if (!callback) {
              showMessage('Spreadsheet saved successfully!', 'success');
            }
            if (typeof callback === 'function') {
              callback();
            }
          } else {
            showMessage('Error saving spreadsheet: ' + data.message, 'error');
          }
        })
        .catch(error => {
          showMessage('An error occurred while saving.', 'error');
          console.error('Error:', error);
        })
        .finally(() => {
          if (!callback) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save';
          }
        });
    }
  
    /**
     * Parse a cell reference (e.g., "A1") into row and column indices.
     * @param {string} ref - The cell reference.
     * @returns {Object|null} The row and col indices or null if invalid.
     */
    function parseCellReference(ref) {
      const match = ref.match(/^([A-Z])(\d+)$/);
      if (!match) return null;
      const colLetter = match[1];
      const rowNum = parseInt(match[2], 10);
      const colIndex = colLetter.charCodeAt(0) - 65; // A=0, B=1, etc.
      const rowIndex = rowNum - 1; // Convert 1-based to 0-based index
      if (rowIndex < 0 || rowIndex >= rows || colIndex < 0 || colIndex >= cols) {
        return null;
      }
      return { row: rowIndex, col: colIndex };
    }
  
    // -------------------------------
    // Formula Evaluation Functions
    // -------------------------------
  
    /**
     * Load and display models for the spreadsheet.
     */
    function loadModels() {
      fetch(`/ml/list/${spreadsheetId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            if (data.models.length > 0) {
              modelsListEl.innerHTML = '';
              data.models.forEach(model => {
                const modelCard = document.createElement('div');
                modelCard.className = 'model-card';
                let metricsHtml = '';
                if (model.type === 'regression') {
                  metricsHtml = `
                    <div class="model-metrics">
                      <p><strong>R² Score:</strong> ${model.metrics.r2.toFixed(4)}</p>
                      <p><strong>Mean Squared Error:</strong> ${model.metrics.mse.toFixed(4)}</p>
                    </div>
                  `;
                } else {
                  metricsHtml = `
                    <div class="model-metrics">
                      <p><strong>Accuracy:</strong> ${model.metrics.accuracy.toFixed(4)}</p>
                    </div>
                  `;
                }

                // Format column names with custom names if available
                const formatColumn = (col) => model.source_column_names[col] || col;
                const inputColumns = model.input_columns.map(formatColumn);
                const outputColumn = formatColumn(model.output_column);
                const inputsExample = model.input_columns.map((col) => `${col}1`).join(', ');
                const formulaExample = `=<span class="model-name">${model.name}</span>(${inputsExample})`;
                
                // Add source spreadsheet info
                const sourceInfo = model.source_spreadsheet.id === parseInt(spreadsheetId) 
                  ? '' 
                  : `<p class="source-info">Trained on spreadsheet: ${model.source_spreadsheet.name}</p>`;
  
                modelCard.innerHTML = `
                  <h4>${model.name}</h4>
                  ${sourceInfo}
                  <p><strong>Type:</strong> ${model.type}</p>
                  <div class="model-columns">
                    <p><strong>Input Columns:</strong></p>
                    <ul class="column-list">
                      ${model.input_columns.map(col => `
                        <li>
                          ${formatColumn(col)}
                          ${model.source_column_types[col] ? 
                            `<span class="col-type type-${model.source_column_types[col]}">${model.source_column_types[col]}</span>` 
                            : ''}
                        </li>
                      `).join('')}
                    </ul>
                    <p><strong>Output Column:</strong></p>
                    <ul class="column-list">
                      <li>
                        ${outputColumn}
                        ${model.source_column_types[model.output_column] ? 
                          `<span class="col-type type-${model.source_column_types[model.output_column]}">${model.source_column_types[model.output_column]}</span>` 
                          : ''}
                      </li>
                    </ul>
                  </div>
                  ${metricsHtml}
                  <div class="formula-example">
                    <p><strong>Usage:</strong> ${formulaExample}</p>
                  </div>
                  <p class="model-id" style="display:none;">${model.id}</p>
                `;
                modelsListEl.appendChild(modelCard);
              });
            } else {
              modelsListEl.innerHTML = '<p>No models created yet.</p>';
            }
          } else {
            modelsListEl.innerHTML = '<p>Error loading models.</p>';
          }
        })
        .catch(error => {
          modelsListEl.innerHTML = '<p>Error loading models.</p>';
          console.error('Error:', error);
        });
    }
  
    /**
     * Evaluate a cell's formula if it starts with "=".
     * @param {HTMLInputElement} inputEl - The cell's input element.
     * @param {number} row - Row index.
     * @param {number} col - Column index.
     */
    function evaluateFormula(inputEl, row, col) {
      const formula = inputEl.value.trim();
      if (!formula.startsWith('=')) return;
  
      // Regex to capture model formula: =ModelName(A1, B1, ...)
      const modelRegex = /^=([A-Za-z0-9_]+)\(([^)]*)\)$/;
      const match = formula.match(modelRegex);
      if (!match) {
        inputEl.classList.add('formula-error');
        inputEl.title = 'Invalid formula format. Use =ModelName(A1, B1, ...)';
        return;
      }
      const modelName = match[1];
      const paramStr = match[2];
      const params = paramStr.split(',').map(p => p.trim());
  
      // If models are not yet cached, load them then evaluate
      if (Object.keys(modelCache).length === 0) {
        fetch(`/ml/list/${spreadsheetId}`)
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              data.models.forEach(model => {
                modelCache[model.name.toLowerCase()] = model;
              });
              evaluateModelFormula(inputEl, row, col, modelName, params);
            }
          })
          .catch(error => {
            inputEl.classList.add('formula-error');
            inputEl.title = 'Error loading models';
          });
      } else {
        evaluateModelFormula(inputEl, row, col, modelName, params);
      }
    }
  
    /**
     * Evaluate the model formula by collecting referenced cell values and calling the evaluation API.
     * @param {HTMLInputElement} inputEl - The cell's input element.
     * @param {number} row - Row index of the cell.
     * @param {number} col - Column index of the cell.
     * @param {string} modelName - The model name.
     * @param {Array<string>} cellRefs - Array of cell references (e.g., ["A1", "B1"]).
     */
    function evaluateModelFormula(inputEl, row, col, modelName, cellRefs) {
      const model = modelCache[modelName.toLowerCase()];
      if (!model) {
        inputEl.classList.add('formula-error');
        inputEl.title = `Model "${modelName}" not found`;
        return;
      }
      if (cellRefs.length !== model.input_columns.length) {
        inputEl.classList.add('formula-error');
        inputEl.title = `Model requires ${model.input_columns.length} inputs, got ${cellRefs.length}`;
        return;
      }
      const inputValues = [];
      let allValid = true;
      for (let i = 0; i < cellRefs.length; i++) {
        const cellRef = cellRefs[i];
        const expectedType = model.source_column_types[model.input_columns[i]];
        const cellCoord = parseCellReference(cellRef);
        if (!cellCoord) {
          inputEl.classList.add('formula-error');
          inputEl.title = `Invalid cell reference: ${cellRef}`;
          allValid = false;
          break;
        }
        const { row: cellRow, col: cellCol } = cellCoord;
        const cellKey = `${cellRow}-${cellCol}`;
        const cellValue = spreadsheetData[cellKey] || '';
        
        // Handle type conversion if needed
        let convertedValue = cellValue;
        if (expectedType === 'number' && cellValue) {
          try {
            convertedValue = parseFloat(cellValue);
            if (isNaN(convertedValue)) {
              inputEl.classList.add('formula-error');
              inputEl.title = `Cell ${cellRef} must contain a numeric value for input ${model.input_columns[i]}`;
              allValid = false;
              break;
            }
          } catch (e) {
            inputEl.classList.add('formula-error');
            inputEl.title = `Error converting cell ${cellRef} to number for input ${model.input_columns[i]}`;
            allValid = false;
            break;
          }
        }
        
        inputValues.push(convertedValue || 0);
      }
      if (!allValid) return;
  
      fetch(`/ml/evaluate/${model.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inputs: inputValues })
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Store the original formula
            const cellKey = `${row}-${col}`;
            spreadsheetData[cellKey] = inputEl.value;
            inputEl.classList.add('formula-cell');
            inputEl.classList.remove('formula-error');
  
            // Show the result (limiting decimals)
            const resultValue = parseFloat(data.result).toFixed(4);
            inputEl.dataset.result = resultValue;
            if (model.type === 'classification') {
              const classValue = parseFloat(resultValue) >= 0.5 ? 1 : 0;
              inputEl.value = classValue;
            } else {
              inputEl.value = resultValue;
            }
            inputEl.title = 'Formula result: ' + resultValue;
          } else {
            inputEl.classList.add('formula-error');
            inputEl.title = data.message;
          }
        })
        .catch(error => {
          inputEl.classList.add('formula-error');
          inputEl.title = 'Error evaluating formula';
          console.error('Error:', error);
        });
    }
  
    // -------------------------------
    // Spreadsheet Grid Initialization
    // -------------------------------
  
    /**
     * Detect the type of a column based on its values.
     * @param {number} col - Column index.
     * @returns {string|null} Column type ('number', 'string', 'mixed', or null if empty).
     */
    function detectColumnType(col) {
      let hasNumber = false;
      let hasString = false;
      let hasNonEmpty = false;
      
      // Check all cells in the column
      for (let r = 0; r < rows; r++) {
        const cellKey = `${r}-${col}`;
        const value = spreadsheetData[cellKey];
        
        if (!value) {
          continue;
        }
        
        hasNonEmpty = true;
        // Check if it's a number
        if (!isNaN(parseFloat(value)) && isFinite(value)) {
          hasNumber = true;
        } else {
          hasString = true;
        }
      }
      
      // If column is completely empty, return null
      if (!hasNonEmpty) {
        return null;
      }
      
      // Determine column type
      if (hasNumber && !hasString) {
        return 'number';
      } else if (hasString && !hasNumber) {
        return 'string';
      } else {
        return 'mixed';
      }
    }
  
    /**
     * Update column headers with type information and custom names.
     */
    function updateColumnHeaders() {
      const headerRow = document.querySelector('.spreadsheet-table tr');
      if (!headerRow) return;
      
      // Skip the first cell (corner cell)
      for (let c = 0; c < cols; c++) {
        const colHeader = headerRow.children[c + 1];
        if (!colHeader) continue;
        
        const colType = detectColumnType(c);
        const colLetter = String.fromCharCode(65 + c);
        
        // Clear existing content
        colHeader.innerHTML = '';
        
        // Create container for column letter and type
        const container = document.createElement('div');
        container.className = 'col-header-container';
        
        // Add column letter/name
        const letterDiv = document.createElement('div');
        letterDiv.className = 'col-letter';
        letterDiv.textContent = columnNames[colLetter] || colLetter;
        letterDiv.dataset.col = colLetter;
        letterDiv.contentEditable = true;
        
        // Add click handler for editing
        letterDiv.addEventListener('click', function(e) {
          e.stopPropagation();
          this.focus();
        });
        
        // Handle blur event to save changes
        letterDiv.addEventListener('blur', function() {
          const newName = this.textContent.trim();
          if (newName) {
            columnNames[this.dataset.col] = newName;
          } else {
            delete columnNames[this.dataset.col];
          }
        });
        
        // Handle keydown events
        letterDiv.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            this.blur();
          } else if (e.key === 'Escape') {
            e.preventDefault();
            this.textContent = columnNames[this.dataset.col] || this.dataset.col;
            this.blur();
          }
        });
        
        container.appendChild(letterDiv);
        
        // Add type indicator if column is not empty
        if (colType) {
          const typeDiv = document.createElement('div');
          typeDiv.className = `col-type type-${colType}`;
          typeDiv.textContent = colType;
          container.appendChild(typeDiv);
        }
        
        colHeader.appendChild(container);
      }
    }
  
    /**
     * Creates and appends the spreadsheet grid (table) to the DOM.
     */
    function initSpreadsheet() {
      const table = document.createElement('table');
      table.className = 'spreadsheet-table';
  
      // Create header row with column labels (A, B, C, ...)
      const headerRow = document.createElement('tr');
      const cornerCell = document.createElement('th');
      headerRow.appendChild(cornerCell);
      for (let c = 0; c < cols; c++) {
        const colHeader = document.createElement('th');
        const colLetter = String.fromCharCode(65 + c);
        const container = document.createElement('div');
        container.className = 'col-header-container';
        
        const letterDiv = document.createElement('div');
        letterDiv.className = 'col-letter';
        letterDiv.textContent = columnNames[colLetter] || colLetter;
        letterDiv.dataset.col = colLetter;
        letterDiv.contentEditable = true;
        
        // Add click handler for editing
        letterDiv.addEventListener('click', function(e) {
          e.stopPropagation();
          this.focus();
        });
        
        // Handle blur event to save changes
        letterDiv.addEventListener('blur', function() {
          const newName = this.textContent.trim();
          if (newName) {
            columnNames[this.dataset.col] = newName;
          } else {
            delete columnNames[this.dataset.col];
          }
        });
        
        // Handle keydown events
        letterDiv.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            this.blur();
          } else if (e.key === 'Escape') {
            e.preventDefault();
            this.textContent = columnNames[this.dataset.col] || this.dataset.col;
            this.blur();
          }
        });
        
        container.appendChild(letterDiv);
        colHeader.appendChild(container);
        headerRow.appendChild(colHeader);
      }
      table.appendChild(headerRow);
  
      // Create data rows
      for (let r = 0; r < rows; r++) {
        const row = document.createElement('tr');
  
        // Row header (1, 2, 3, ...)
        const rowHeader = document.createElement('th');
        rowHeader.className = 'row-header';
        rowHeader.textContent = r + 1;
        row.appendChild(rowHeader);
  
        // Data cells
        for (let c = 0; c < cols; c++) {
          const cell = document.createElement('td');
          const input = document.createElement('input');
          input.className = 'cell';
          input.dataset.row = r;
          input.dataset.col = c;
  
          // Load data if it exists
          const cellKey = `${r}-${c}`;
          if (spreadsheetData[cellKey]) {
            input.value = spreadsheetData[cellKey];
            if (input.value && input.value.startsWith('=')) {
              evaluateFormula(input, r, c);
            }
          }
  
          // Update data on change
          input.addEventListener('change', function () {
            updateData(r, c, input.value);
            if (input.value && input.value.startsWith('=')) {
              evaluateFormula(input, r, c);
            }
            // Update column headers after data change
            updateColumnHeaders();
          });

          // Handle mouse events for selection
          input.addEventListener('mousedown', function(e) {
            isSelecting = true;
            selectionStart = { row: r, col: c };
            selectionEnd = { row: r, col: c };
            updateSelection();
            e.preventDefault(); // Prevent focus from being removed
          });

          input.addEventListener('mouseover', function(e) {
            if (isSelecting) {
              selectionEnd = { row: r, col: c };
              updateSelection();
            }
          });

          document.addEventListener('mouseup', function(e) {
            if (isSelecting) {
              isSelecting = false;
              // Focus the last selected cell
              const lastCell = document.querySelector(
                `.cell[data-row="${selectionEnd.row}"][data-col="${selectionEnd.col}"]`
              );
              if (lastCell) {
                lastCell.focus();
              }
            }
          });

          // Handle copy event
          input.addEventListener('copy', function(e) {
            if (!selectionStart || !selectionEnd) return;
            
            e.preventDefault();
            
            // Get the bounds of the selection
            const minRow = Math.min(selectionStart.row, selectionEnd.row);
            const maxRow = Math.max(selectionStart.row, selectionEnd.row);
            const minCol = Math.min(selectionStart.col, selectionEnd.col);
            const maxCol = Math.max(selectionStart.col, selectionEnd.col);
            
            // Build the copied data
            const copiedData = [];
            for (let row = minRow; row <= maxRow; row++) {
              const rowData = [];
              for (let col = minCol; col <= maxCol; col++) {
                const cellKey = `${row}-${col}`;
                rowData.push(spreadsheetData[cellKey] || '');
              }
              copiedData.push(rowData.join('\t'));
            }
            
            // Copy to clipboard
            e.clipboardData.setData('text', copiedData.join('\n'));
          });

          // Handle paste events for multi-cell paste
          input.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedData = e.clipboardData.getData('text');
            const pastedRows = pastedData.split('\n').map(row => row.split('\t'));
            
            // Get the starting position
            const startRow = parseInt(input.dataset.row);
            const startCol = parseInt(input.dataset.col);
            
            // Process each row and column
            pastedRows.forEach((row, rowOffset) => {
              row.forEach((value, colOffset) => {
                const targetRow = startRow + rowOffset;
                const targetCol = startCol + colOffset;
                
                // Check if we're within bounds
                if (targetRow < rows && targetCol < cols) {
                  const targetCell = document.querySelector(
                    `.cell[data-row="${targetRow}"][data-col="${targetCol}"]`
                  );
                  if (targetCell) {
                    targetCell.value = value;
                    updateData(targetRow, targetCol, value);
                    if (value && value.startsWith('=')) {
                      evaluateFormula(targetCell, targetRow, targetCol);
                    }
                  }
                }
              });
            });
          });

          input.addEventListener('focus', function () {
            selectedCell = input;
            const cellKey = `${r}-${c}`;
            const rawValue = spreadsheetData[cellKey];
            // Show raw formula if available, otherwise show displayed value
            if (rawValue && rawValue.startsWith('=')) {
              editorInput.value = rawValue;
            } else {
              editorInput.value = input.value;
            }
            // Clear any existing selection when focusing a cell
            if (!isSelecting) {
              selectionStart = null;
              selectionEnd = null;
              updateSelection();
            }
          });
  
          // Keyboard navigation for cells
          input.addEventListener('keydown', function (e) {
            const currentRow = parseInt(input.dataset.row);
            const currentCol = parseInt(input.dataset.col);
            let nextRow = currentRow;
            let nextCol = currentCol;
            switch (e.key) {
              case 'ArrowUp':
                nextRow = Math.max(0, currentRow - 1);
                break;
              case 'ArrowDown':
                nextRow = Math.min(rows - 1, currentRow + 1);
                break;
              case 'ArrowLeft':
                nextCol = Math.max(0, currentCol - 1);
                break;
              case 'ArrowRight':
                nextCol = Math.min(cols - 1, currentCol + 1);
                break;
              case 'Tab':
                e.preventDefault();
                if (e.shiftKey) {
                  if (currentCol > 0) {
                    nextCol = currentCol - 1;
                  } else if (currentRow > 0) {
                    nextRow = currentRow - 1;
                    nextCol = cols - 1;
                  }
                } else {
                  if (currentCol < cols - 1) {
                    nextCol = currentCol + 1;
                  } else if (currentRow < rows - 1) {
                    nextRow = currentRow + 1;
                    nextCol = 0;
                  }
                }
                break;
              case 'Enter':
                e.preventDefault();
                if (e.shiftKey) {
                  nextRow = Math.max(0, currentRow - 1);
                } else {
                  nextRow = Math.min(rows - 1, currentRow + 1);
                }
                break;
              default:
                return;
            }
            if (nextRow !== currentRow || nextCol !== currentCol) {
              const nextCell = document.querySelector(
                `.cell[data-row="${nextRow}"][data-col="${nextCol}"]`
              );
              if (nextCell) {
                nextCell.focus();
                nextCell.select();
              }
            }
          });
  
          cell.appendChild(input);
          row.appendChild(cell);
        }
        table.appendChild(row);
      }
      spreadsheetEl.appendChild(table);
      
      // Update column headers with type information
      updateColumnHeaders();
    }
  
    // -------------------------------
    // Editor Input Synchronization
    // -------------------------------
    // When the user types in the editor bar, update the selected cell's value.
    if (editorInput) {
      editorInput.addEventListener('input', function () {
        if (selectedCell) {
          selectedCell.value = editorInput.value;
          updateData(selectedCell.dataset.row, selectedCell.dataset.col, editorInput.value);
          // Evaluate formula if it starts with '='
          if (editorInput.value && editorInput.value.startsWith('=')) {
            evaluateFormula(selectedCell, selectedCell.dataset.row, selectedCell.dataset.col);
          }
        }
      });
    }
  
    // -------------------------------
    // Model Loading and Modal Functionality
    // -------------------------------
  
    // Modal and Model Creation Elements
    const modelModal = document.getElementById('create-model-modal');
    const closeModelBtn = modelModal.querySelector('.close');
    const cancelModelBtn = modelModal.querySelector('.btn-cancel');
    const createModelForm = document.getElementById('create-model-form');
    const inputColumnsContainer = document.getElementById('input-columns-container');
    const outputColumnSelect = document.getElementById('output_column');
  
    // Open the model creation modal and populate column options
    createModelBtn.addEventListener('click', function () {
      populateColumnOptions();
      modelModal.style.display = 'block';
    });
  
    // Close modal events
    closeModelBtn.addEventListener('click', function () {
      modelModal.style.display = 'none';
    });
    cancelModelBtn.addEventListener('click', function () {
      modelModal.style.display = 'none';
    });
    window.addEventListener('click', function (event) {
      if (event.target === modelModal) {
        modelModal.style.display = 'none';
      }
    });
  
    /**
     * Populate column options for the model creation form.
     */
    function populateColumnOptions() {
      inputColumnsContainer.innerHTML = '';
      outputColumnSelect.innerHTML = '<option value="">Select a column</option>';
      for (let c = 0; c < cols; c++) {
        const colLetter = String.fromCharCode(65 + c);
        const colName = columnNames[colLetter] || colLetter;
  
        // Create input checkbox for each column
        const checkboxDiv = document.createElement('div');
        checkboxDiv.className = 'column-checkbox';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'input_columns';
        checkbox.value = colLetter;
        checkbox.id = `input_col_${colLetter}`;
        const label = document.createElement('label');
        label.htmlFor = `input_col_${colLetter}`;
        label.textContent = colName;
        checkboxDiv.appendChild(checkbox);
        checkboxDiv.appendChild(label);
        inputColumnsContainer.appendChild(checkboxDiv);
  
        // Create option for output column
        const option = document.createElement('option');
        option.value = colLetter;
        option.textContent = colName;
        outputColumnSelect.appendChild(option);
      }
    }
  
    // Handle form submission for model creation
    createModelForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const submitBtn = createModelForm.querySelector('[type="submit"]');
      const originalBtnText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating...';
      const formData = new FormData(createModelForm);
      const inputCols = formData.getAll('input_columns');
      const outputCol = formData.get('output_column');
  
      if (inputCols.length === 0) {
        showMessage('Please select at least one input column', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        return;
      }
      if (inputCols.includes(outputCol)) {
        showMessage('Output column cannot also be an input column', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        return;
      }
  
      // Save the spreadsheet first, then submit the model creation
      saveSpreadsheet(function () {
        fetch('/ml/create', {
          method: 'POST',
          body: formData
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              showMessage('Model created successfully!', 'success');
              modelModal.style.display = 'none';
              loadModels();
            } else {
              showMessage('Error creating model: ' + data.message, 'error');
            }
          })
          .catch(error => {
            showMessage('An error occurred while creating the model.', 'error');
            console.error('Error:', error);
          })
          .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
          });
      });
    });
  
    // -------------------------------
    // Final Initialization and Event Bindings
    // -------------------------------
    initSpreadsheet();
    loadModels();
  
    // Save button event
    saveBtn.addEventListener('click', function () {
      saveSpreadsheet();
    });
  
    // Keyboard shortcut for save (Ctrl+S)
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveSpreadsheet();
      }
    });

    /**
     * Update the visual selection of cells
     */
    function updateSelection() {
      // Remove selection from all cells
      document.querySelectorAll('.cell').forEach(cell => {
        cell.classList.remove('selected');
      });

      if (!selectionStart || !selectionEnd) return;

      // Get the bounds of the selection
      const minRow = Math.min(selectionStart.row, selectionEnd.row);
      const maxRow = Math.max(selectionStart.row, selectionEnd.row);
      const minCol = Math.min(selectionStart.col, selectionEnd.col);
      const maxCol = Math.max(selectionStart.col, selectionEnd.col);

      // Add selection to cells within bounds
      for (let row = minRow; row <= maxRow; row++) {
        for (let col = minCol; col <= maxCol; col++) {
          const cell = document.querySelector(
            `.cell[data-row="${row}"][data-col="${col}"]`
          );
          if (cell) {
            cell.classList.add('selected');
          }
        }
      }
    }
  });
  