import os
import logging
import dataiku
from dataiku.customrecipe import get_plugin_config, get_input_names_for_role, get_output_names_for_role
from dku_neo4j.neo4j_handle import Neo4jHandle
import gzip

# This file contains stuff that is common across this plugin recipes but that are not part of
# our dku_neo4j wrapper library. In particular, dku_neo4j library does not depend on any DSS code
# so anything specific to DSS APIs is here


def get_neo4jhandle():
    neo4jhandle = Neo4jHandle(
        get_plugin_config().get("neo4jUri"),
        get_plugin_config().get("neo4jUsername"),
        get_plugin_config().get("neo4jPassword"),
    )
    neo4jhandle.check()
    return neo4jhandle


def get_input_output():
    if len(get_input_names_for_role("input_dataset")) == 0:
        raise ValueError("No input dataset.")
    input_dataset_name = get_input_names_for_role("input_dataset")[0]
    input_dataset = dataiku.Dataset(input_dataset_name)

    output_folder_name = get_output_names_for_role("output_folder")[0]
    output_folder = dataiku.Folder(output_folder_name)
    return (input_dataset, output_folder)


class GeneralExportParams:
    def __init__(self, recipe_config):
        self.expert_mode = recipe_config.get("expert_mode", False)
        self.load_from_csv = recipe_config.get("load_from_csv", False)
        self.csv_size = recipe_config.get("csv_size")
        self.batch_size = recipe_config.get("batch_size")

        if not self.expert_mode:
            self.load_from_csv = False
            self.csv_size = 100000
            self.batch_size = 500

        if self.load_from_csv:
            self.batch_size = self.csv_size

        neo4j_server_configuration = recipe_config.get("neo4j_server_configuration")
        self.uri = neo4j_server_configuration.get("neo4j_uri")
        self.username = neo4j_server_configuration.get("neo4j_username")
        self.password = neo4j_server_configuration.get("neo4j_password")

    def check(self):
        if not isinstance(self.batch_size, int) or self.batch_size < 1:
            label = "CSV size" if self.load_from_csv else "Batch size"
            raise ValueError(f"{label} must be an integer greater than 1.")


class ImportFileHandler:
    """Class to write and delete dataframe as csv file into a dataiku.Folder """

    def __init__(self, folder):
        self.folder = folder

    def write(self, df, path):
        """Write df to path in Folder as a compressed csv. Returns the complete path of the import directory"""
        string_buf = df.to_csv(sep=",", na_rep="", header=False, index=False)
        with self.folder.get_writer(path=path) as writer:
            with gzip.GzipFile(fileobj=writer, mode="wb") as fgzip:
                logging.info(f"Writing file: {path}")
                fgzip.write(string_buf.encode())
        full_path = os.path.join(self.folder.project_key, self.folder.short_name, path)
        return full_path

    def delete(self, path):
        logging.info(f"Deleting file: {path}")
        self.folder.delete_path(path)


def create_dataframe_iterator(dataset, batch_size=10000, columns=None):
    for df in dataset.iter_dataframes(
        chunksize=batch_size, columns=columns, parse_dates=False, infer_with_pandas=False
    ):
        yield df
