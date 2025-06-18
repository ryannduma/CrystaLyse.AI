# CrystaLyse.AI Piezoelectric Materials Stress Test Report

**Date**: 2025-06-18T12:39:18.373924  
**Test Type**: Piezoelectric Materials Discovery

## Executive Summary

This stress test evaluates CrystaLyse.AI's performance in discovering piezoelectric materials using both Creative and Rigorous modes.

## Test Results

### Creative Mode Test

**Query**: "Explore novel piezoelectric materials"  
**Status**: ✅ Success  
**Execution Time**: 24.58 seconds  
**Model Used**: o4-mini  
**Compositions Generated**: 9

#### Performance Metrics
- Total Cost: $0.000
- Tool Calls: 0
- Success Rate: 0.0%

### Rigorous Mode Test

**Query**: "Find stable lead-free piezoelectric for medical devices"  
**Status**: ✅ Success  
**Execution Time**: 45.99 seconds  
**Model Used**: o3  

#### Validation Metrics
- Compositions Validated: 10
- Structures Predicted: 52
- Energy Calculations: 25

#### Performance Metrics
- Total Cost: $0.000
- Tool Calls: 0
- Success Rate: 0.0%

## Mode Comparison

- **Time Difference**: 21.41 seconds
- **Speedup Factor**: 1.87x
- **Creative Mode Faster By**: 46.5%
- **Validation Overhead**: SMACT validation + structure prediction + energy calculations

### Recommendation
Use Creative Mode for initial exploration, Rigorous Mode for final validation

## Conclusions

1. **Creative Mode** provides rapid exploration of chemical space, ideal for initial discovery
2. **Rigorous Mode** ensures validated results with computational verification
3. The modes are complementary: use Creative for breadth, Rigorous for depth
4. Time-performance trade-off aligns with expected behaviour (~2x slower for full validation)

## Error Summary

No errors encountered during testing. ✅

---
*Report generated on 2025-06-18 12:40:30*
