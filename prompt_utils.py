
def generate_path(pathdata):
    for i in range(len(pathdata)):
        #pathdata[i]=pathdata[i].replace('\n','')
        pathdata[i]=f"'{pathdata[i]}'"
    path_prompt=' -> '.join(pathdata)
    return path_prompt
