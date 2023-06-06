# Compiles the bitvis uvvm library sources
# Loads bitvis components listed in bitvis_component_list.txt

# Update relativ path to bitvis library
quietly set bitvis_path ../../../../bitvis
quietly set current_path [pwd]/../scripts
quietly set lib_path [pwd]/../libs
do $bitvis_path/script/compile_all.do $bitvis_path/script/ $lib_path $current_path/bitvis_component_list.txt