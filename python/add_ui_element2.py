import xml.etree.ElementTree as ET
import sys

tree = ET.parse('cwsimgui.ui')
root = tree.getroot()

# Find gridLayout_6 and append our widgets
for layout in root.iter('layout'):
    if layout.get('name') == 'gridLayout_6':
        
        names = [widget.get('name') for widget in layout.iter('widget') if widget.get('name')]
        if 'straightKeyLabel' in names:
            break

        item_label = ET.Element('item', attrib={'row': '4', 'column': '0'})
        widget_label = ET.SubElement(item_label, 'widget', attrib={'class': 'QLabel', 'name': 'straightKeyLabel'})
        prop_text = ET.SubElement(widget_label, 'property', attrib={'name': 'text'})
        string_text = ET.SubElement(prop_text, 'string')
        string_text.text = 'Straight Key %'
        layout.append(item_label)
        
        item_spin = ET.Element('item', attrib={'row': '4', 'column': '1'})
        widget_spin = ET.SubElement(item_spin, 'widget', attrib={'class': 'QDoubleSpinBox', 'name': 'straightKeyProbSpinBox'})
        
        prop_focus = ET.SubElement(widget_spin, 'property', attrib={'name': 'focusPolicy'})
        enum_focus = ET.SubElement(prop_focus, 'enum')
        enum_focus.text = 'Qt::StrongFocus'
        
        prop_tt = ET.SubElement(widget_spin, 'property', attrib={'name': 'toolTip'})
        string_tt = ET.SubElement(prop_tt, 'string')
        string_tt.text = 'Probability of stations using a straight key (0 to 1)'
        
        prop_an = ET.SubElement(widget_spin, 'property', attrib={'name': 'accessibleName'})
        string_an = ET.SubElement(prop_an, 'string')
        string_an.text = 'Straight Key probability'
        
        prop_max = ET.SubElement(widget_spin, 'property', attrib={'name': 'maximum'})
        double_max = ET.SubElement(prop_max, 'double')
        double_max.text = '1.000000000000000'

        prop_step = ET.SubElement(widget_spin, 'property', attrib={'name': 'singleStep'})
        double_step = ET.SubElement(prop_step, 'double')
        double_step.text = '0.010000000000000'
        
        layout.append(item_spin)
        
        break

# Insert tabstop just after lidsCheck
tabstops = root.find('.//tabstops')
if tabstops is not None:
    # Find index of lidsCheck
    insert_idx = -1
    for i, ts in enumerate(list(tabstops)):
        if ts.text == 'lidsCheck':
            insert_idx = i + 1
            break
    
    if insert_idx != -1:
        new_ts = ET.Element('tabstop')
        new_ts.text = 'straightKeyProbSpinBox'
        tabstops.insert(insert_idx, new_ts)

tree.write('cwsimgui.ui', encoding='utf-8', xml_declaration=True)
print("Successfully updated cwsimgui.ui")
