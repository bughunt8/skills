#!/usr/bin/env node

/**
 * TOGAF Artifacts Validator
 * 
 * This script validates TOGAF architecture artifacts for:
 * - Required sections in documents
 * - Proper structure in deliverables
 * - Cross-references between artifacts
 */

const fs = require('fs');
const path = require('path');

// Define validation rules for different artifact types
const validationRules = {
  'architecture-vision': {
    requiredSections: [
      '业务背景',
      '架构愿景',
      '利益相关者',
      '价值主张'
    ],
    optionalSections: [
      '高层路线图',
      '风险'
    ]
  },
  'business-architecture': {
    requiredSections: [
      '概述',
      '基线业务架构',
      '目标业务架构',
      '差距分析'
    ]
  },
  'data-architecture': {
    requiredSections: [
      '概述',
      '数据原则',
      '概念数据模型',
      '数据实体目录'
    ]
  },
  'application-architecture': {
    requiredSections: [
      '概述',
      '应用原则',
      '应用组合目录',
      '应用交互'
    ]
  },
  'technology-architecture': {
    requiredSections: [
      '概述',
      '技术原则',
      '技术标准目录',
      '部署架构'
    ]
  },
  'principles': {
    requiredFields: [
      'ID',
      '名称',
      '声明',
      '依据',
      '影响'
    ]
  },
  'building-blocks': {
    requiredFields: [
      'ID',
      '名称',
      '类型',
      '描述',
      '能力'
    ]
  }
};

/**
 * Validate a markdown document against rules
 */
function validateDocument(content, artifactType) {
  const results = {
    valid: true,
    errors: [],
    warnings: []
  };

  const rules = validationRules[artifactType];
  if (!rules) {
    results.warnings.push(`No validation rules defined for artifact type: ${artifactType}`);
    return results;
  }

  // Check required sections
  if (rules.requiredSections) {
    for (const section of rules.requiredSections) {
      if (!content.includes(section)) {
        results.errors.push(`Missing required section: ${section}`);
        results.valid = false;
      }
    }
  }

  // Check required fields (for structured content like principles)
  if (rules.requiredFields) {
    for (const field of rules.requiredFields) {
      const regex = new RegExp(`${field}\\s*[:：]`, 'i');
      if (!regex.test(content)) {
        results.errors.push(`Missing required field: ${field}`);
        results.valid = false;
      }
    }
  }

  return results;
}

/**
 * Validate cross-references between artifacts
 */
function validateCrossReferences(artifacts) {
  const results = {
    valid: true,
    errors: [],
    warnings: []
  };

  // Check that referenced IDs exist
  const allIds = new Set();
  const references = [];

  for (const artifact of artifacts) {
    // Extract IDs defined in this artifact
    const idMatches = artifact.content.match(/ID\s*[:：]\s*([\w-]+)/gi) || [];
    for (const match of idMatches) {
      const id = match.split(/[:：]/)[1].trim();
      allIds.add(id);
    }

    // Extract references to other artifacts
    const refMatches = artifact.content.match(/参考\s*[:：]\s*([\w-]+)/gi) || [];
    const relatedMatches = artifact.content.match(/相关\s*[:：]\s*([\w-]+)/gi) || [];
    
    for (const match of [...refMatches, ...relatedMatches]) {
      const ref = match.split(/[:：]/)[1].trim();
      references.push({ source: artifact.name, target: ref });
    }
  }

  // Validate references
  for (const ref of references) {
    if (!allIds.has(ref.target)) {
      results.warnings.push(`Reference to unknown ID '${ref.target}' in ${ref.source}`);
    }
  }

  return results;
}

/**
 * Validate ADM phase deliverables
 */
function validateADMDeliverables(phase, deliverables) {
  const phaseDeliverables = {
    'preliminary': ['架构原则', '组织模型', '定制框架'],
    'phase-a': ['架构工作声明', '架构愿景', '利益相关者矩阵'],
    'phase-b': ['业务架构文档', '业务能力地图', '业务流程模型'],
    'phase-c': ['数据架构文档', '应用架构文档', '数据模型'],
    'phase-d': ['技术架构文档', '技术标准目录', '部署图'],
    'phase-e': ['架构路线图', '工作包定义', 'SBB定义'],
    'phase-f': ['迁移计划', '过渡架构'],
    'phase-g': ['架构合同', '合规评估'],
    'phase-h': ['变更请求', '评估报告']
  };

  const results = {
    valid: true,
    missing: [],
    present: []
  };

  const required = phaseDeliverables[phase] || [];
  
  for (const deliverable of required) {
    const found = deliverables.some(d => 
      d.toLowerCase().includes(deliverable.toLowerCase())
    );
    
    if (found) {
      results.present.push(deliverable);
    } else {
      results.missing.push(deliverable);
      results.valid = false;
    }
  }

  return results;
}

/**
 * Main validation function
 */
function validate(inputPath, artifactType) {
  console.log('TOGAF Artifacts Validator');
  console.log('========================\n');

  if (!fs.existsSync(inputPath)) {
    console.error(`Error: Path not found: ${inputPath}`);
    process.exit(1);
  }

  const stats = fs.statSync(inputPath);
  
  if (stats.isFile()) {
    // Validate single file
    const content = fs.readFileSync(inputPath, 'utf-8');
    const results = validateDocument(content, artifactType);
    
    console.log(`Validating: ${inputPath}`);
    console.log(`Artifact Type: ${artifactType}`);
    console.log(`Valid: ${results.valid}`);
    
    if (results.errors.length > 0) {
      console.log('\nErrors:');
      results.errors.forEach(e => console.log(`  - ${e}`));
    }
    
    if (results.warnings.length > 0) {
      console.log('\nWarnings:');
      results.warnings.forEach(w => console.log(`  - ${w}`));
    }
    
  } else if (stats.isDirectory()) {
    // Validate all markdown files in directory
    const files = fs.readdirSync(inputPath)
      .filter(f => f.endsWith('.md'))
      .map(f => ({
        name: f,
        path: path.join(inputPath, f),
        content: fs.readFileSync(path.join(inputPath, f), 'utf-8')
      }));

    console.log(`Found ${files.length} markdown files\n`);

    let allValid = true;
    
    for (const file of files) {
      // Auto-detect artifact type from filename or content
      let type = artifactType;
      if (!type) {
        if (file.name.includes('vision')) type = 'architecture-vision';
        else if (file.name.includes('business')) type = 'business-architecture';
        else if (file.name.includes('data')) type = 'data-architecture';
        else if (file.name.includes('application')) type = 'application-architecture';
        else if (file.name.includes('technology')) type = 'technology-architecture';
        else if (file.name.includes('principle')) type = 'principles';
        else if (file.name.includes('building-block')) type = 'building-blocks';
      }

      if (type) {
        const results = validateDocument(file.content, type);
        console.log(`${file.name}: ${results.valid ? 'VALID' : 'INVALID'}`);
        
        if (!results.valid) {
          allValid = false;
          results.errors.forEach(e => console.log(`  ERROR: ${e}`));
        }
        results.warnings.forEach(w => console.log(`  WARNING: ${w}`));
      } else {
        console.log(`${file.name}: SKIPPED (unknown type)`);
      }
    }

    // Cross-reference validation
    console.log('\nCross-Reference Validation:');
    const crossRefResults = validateCrossReferences(files);
    crossRefResults.warnings.forEach(w => console.log(`  WARNING: ${w}`));

    console.log(`\nOverall: ${allValid ? 'ALL VALID' : 'SOME INVALID'}`);
  }
}

// CLI handling
const args = process.argv.slice(2);
if (args.length < 1) {
  console.log('Usage: node validate-artifacts.js <path> [artifact-type]');
  console.log('\nArtifact types:');
  Object.keys(validationRules).forEach(t => console.log(`  - ${t}`));
  process.exit(0);
}

validate(args[0], args[1]);
