const fs = require('fs');
const path = require('path');

const hooks = [
  {
    name: 'validate-input',
    type: 'pre',
    tool: 'bash',
    description: 'Validate input before bash execution',
    script: 'validate-input.sh'
  },
  {
    name: 'log-action',
    type: 'post',
    tool: 'any',
    description: 'Log all AI actions',
    script: 'log-action.sh'
  },
  {
    name: 'validate-file-write',
    type: 'pre',
    tool: 'write',
    description: 'Validate file writes',
    script: 'validate-file-write.sh'
  }
];

module.exports = hooks;