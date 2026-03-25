import xml.etree.ElementTree as ET
import sys

tree = ET.parse('cwsimgui.ui')
root = tree.getroot()

# Find contestBox gridLayout_5 to add the typeComboBox
for layout in root.iter('layout'):
    if layout.get('name') == 'gridLayout_5':
        names = [widget.get('name') for widget in layout.iter('widget') if widget.get('name')]
        if 'typeComboBox' in names:
            break
            
        # We have:
        # row 0, col 0: contestComboBox (Pileup/Single)
        # row 0, col 1: durationComboBox (Min/QSO)
        # row 0, col 2: activityLabel
        # row 0, col 3: startStopButton
        # Let's shift things or add to a new row. Adding a new combobox in a new place: row 1, col 0
        
        item_combo = ET.Element('item', attrib={'row': '1', 'column': '0', 'colspan': '2'})
        widget_combo = ET.SubElement(item_combo, 'widget', attrib={'class': 'QComboBox', 'name': 'typeComboBox'})
        
        prop_focus = ET.SubElement(widget_combo, 'property', attrib={'name': 'focusPolicy'})
        enum_focus = ET.SubElement(prop_focus, 'enum')
        enum_focus.text = 'Qt::TabFocus'
        
        prop_tt = ET.SubElement(widget_combo, 'property', attrib={'name': 'toolTip'})
        string_tt = ET.SubElement(prop_tt, 'string')
        string_tt.text = 'Choose operating mode'
        
        prop_an = ET.SubElement(widget_combo, 'property', attrib={'name': 'accessibleName'})
        string_an = ET.SubElement(prop_an, 'string')
        string_an.text = 'Operating Mode'
        
        # Item 1: Contest
        item1 = ET.SubElement(widget_combo, 'item')
        prop_text1 = ET.SubElement(item1, 'property', attrib={'name': 'text'})
        string_text1 = ET.SubElement(prop_text1, 'string')
        string_text1.text = 'Contest'
        
        # Item 2: DX Expedition
        item2 = ET.SubElement(widget_combo, 'item')
        prop_text2 = ET.SubElement(item2, 'property', attrib={'name': 'text'})
        string_text2 = ET.SubElement(prop_text2, 'string')
        string_text2.text = 'DX Expedition'
        
        layout.append(item_combo)
        
        break

# Insert tabstop just after contestComboBox
tabstops = root.find('.//tabstops')
if tabstops is not None:
    insert_idx = -1
    for i, ts in enumerate(list(tabstops)):
        if ts.text == 'contestComboBox':
            insert_idx = i + 1
            break
    
    if insert_idx != -1:
        new_ts = ET.Element('tabstop')
        new_ts.text = 'typeComboBox'
        tabstops.insert(insert_idx, new_ts)

tree.write('cwsimgui.ui', encoding='utf-8', xml_declaration=True)
print("Successfully added typeComboBox to cwsimgui.ui")
