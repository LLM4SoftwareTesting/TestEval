

def generate_path(pathdata):
    #pathdata=pathdata[1:-1] #remove start and end, not neede in the newest data version
    for i in range(len(pathdata)):
        #pathdata[i]=pathdata[i].replace('\n','')
        pathdata[i]=f"'{pathdata[i]}'"
    path_prompt=' -> '.join(pathdata)
    #path_prompt=', '.join(pathdata)
    return path_prompt