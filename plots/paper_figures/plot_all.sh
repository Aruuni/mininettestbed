FIGURES="1 3 4 5 6 7 8 9 10 11 12"

plot_in_folder() {
    folder_name="figure$1"
    if [ -d "$folder_name" ]; then
        cd "$folder_name" || exit
        if [ "$folder_name" == "figure11" ]; then
            python3 plot_figure_11.py 23 &
        else
            python3 plot* &
        fi
        cd .. || exit
    else
        echo "Directory $folder_name does not exist."
    fi
}

for fig in $FIGURES
do
    plot_in_folder $fig
    
done

wait