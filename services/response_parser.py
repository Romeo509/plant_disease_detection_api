"""
Response parsing utilities for plant condition analysis
"""
from typing import Dict, Any


class PlantConditionParser:
    """Parser for AI responses to extract structured plant condition data"""
    
    @staticmethod
    def get_default_result() -> Dict[str, str]:
        """Get default analysis result structure"""
        return {
            'plant_type': 'Unknown',
            'disease_status': 'Unknown',
            'control_treatment': 'No treatment information available'
        }
    
    @staticmethod
    def get_treatment_recommendations() -> Dict[str, str]:
        """Get predefined treatment recommendations for each condition"""
        return {
            'maize_streak_virus': 'Use resistant maize varieties. Practice crop rotation and control aphid vectors with approved insecticides.',
            'northern_corn_leaf_blight': 'Apply tebuconazole fungicide. Use resistant varieties and ensure proper field hygiene.',
            'common_rust': 'Apply tebuconazole fungicide. Remove infected plant debris and plant resistant varieties.',
            'fall_armyworm': 'Use emamectin benzoate or neem-based insecticides. Practice early planting and crop rotation.',
            'stem_borers': 'Apply emamectin benzoate during early infestation. Use resistant varieties and practice field hygiene.',
            'maize_weevils': 'Ensure proper grain drying and storage. Use hermetic storage bags or appropriate grain protectants.',
            'healthy': 'Continue with good agricultural practices and regular monitoring.'
        }
    
    def parse_legacy_response(self, content: str) -> Dict[str, str]:
        """
        Parse legacy structured response format (numbered format)
        This method is kept for backward compatibility
        """
        lines = content.strip().split('\n')
        result = self.get_default_result()

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('1.') and 'plant type' in line.lower():
                current_section = 'plant_type'
                parts = line.split(':', 1)
                if len(parts) > 1:
                    result['plant_type'] = parts[1].strip()
            elif line.startswith('2.') and 'disease status' in line.lower():
                current_section = 'disease_status'
                parts = line.split(':', 1)
                if len(parts) > 1:
                    result['disease_status'] = parts[1].strip()
            elif line.startswith('3.') and ('control' in line.lower() or 'treatment' in line.lower()):
                current_section = 'control_treatment'
                parts = line.split(':', 1)
                if len(parts) > 1:
                    result['control_treatment'] = parts[1].strip()
            elif current_section and not line.startswith(('1.', '2.', '3.')):
                if result[current_section] in ['Unknown', 'No treatment information available']:
                    result[current_section] = line
                else:
                    result[current_section] += ' ' + line

        return result
    
    def parse_ai_response(self, ai_response: str) -> Dict[str, str]:
        """
        Parse AI response to extract structured plant condition information
        """
        result = self.get_default_result()
        treatments = self.get_treatment_recommendations()
        
        # Convert to lowercase for case-insensitive matching
        response_lower = ai_response.lower()
        
        # Check for plant type first
        if "not maize" in response_lower:
            result['plant_type'] = 'Not maize'
            result['disease_status'] = 'Not applicable'
            result['control_treatment'] = 'Not applicable'
            return result
        
        # If it's maize, set plant type
        result['plant_type'] = 'Maize'
        
        # Check for specific conditions
        if "maize streak virus" in response_lower:
            result['disease_status'] = 'Maize Streak Virus'
            result['control_treatment'] = treatments['maize_streak_virus']
        elif "northern corn leaf blight" in response_lower:
            result['disease_status'] = 'Northern Corn Leaf Blight'
            result['control_treatment'] = treatments['northern_corn_leaf_blight']
        elif "common rust" in response_lower:
            result['disease_status'] = 'Common Rust'
            result['control_treatment'] = treatments['common_rust']
        elif "fall armyworm" in response_lower:
            result['disease_status'] = 'Fall Armyworm'
            result['control_treatment'] = treatments['fall_armyworm']
        elif "stem borers" in response_lower or "stem borer" in response_lower:
            result['disease_status'] = 'Stem Borers'
            result['control_treatment'] = treatments['stem_borers']
        elif "maize weevils" in response_lower or "maize weevil" in response_lower:
            result['disease_status'] = 'Maize Weevils'
            result['control_treatment'] = treatments['maize_weevils']
        elif "healthy" in response_lower:
            result['disease_status'] = 'Healthy'
            result['control_treatment'] = treatments['healthy']
        
        return result