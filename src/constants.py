class Constants:
    imageA_default_path = "imageA.jpg"
    imageB_default_path = "imageB.jpg"
    
    @staticmethod
    def imageA_point_path():
        return f"points/{Constants.imageA_default_path}_points.csv"
    
    @staticmethod
    def imageB_point_path():
        return f"points/{Constants.imageB_default_path}_points.csv"
