"""
Copyright (c) 2017, 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""
from java.io import File
from java.io import IOException
from java.lang import IllegalArgumentException
from java.lang import SecurityException
from java.net import URI
from java.net import URISyntaxException
from java.net import MalformedURLException

from oracle.weblogic.deploy.util import FileUtils
from oracle.weblogic.deploy.util import PyOrderedDict as OrderedDict
from oracle.weblogic.deploy.util import WLSDeployArchiveIOException

from wlsdeploy.aliases import model_constants
from wlsdeploy.aliases.location_context import LocationContext
from wlsdeploy.aliases.wlst_modes import WlstModes
from wlsdeploy.logging.platform_logger import PlatformLogger
from wlsdeploy.tool.discover import discoverer
from wlsdeploy.tool.discover.discoverer import Discoverer

_class_name = 'CoherenceResourcesDiscoverer'
_logger = PlatformLogger(discoverer.get_discover_logger_name())


class CoherenceResourcesDiscoverer(Discoverer):
    """
    Discover the weblogic coherence resources from the domain.
    """

    def __init__(self, model_context, resource_dictionary, wlst_mode=WlstModes.OFFLINE,
                 base_location=LocationContext()):
        """
        Initialize this discoverer instance with the specific information needed to discover coherence resources.
        :param model_context: context about the model for this instance of discover domain
        :param resource_dictionary: was provided on the discover call, else use initialized resources
        :param base_location: current context for discover or new context if not provided
        """
        Discoverer.__init__(self, model_context, wlst_mode, base_location)
        self._dictionary = resource_dictionary
        self._add_att_handler(model_constants.COHERENCE_CUSTOM_CLUSTER_CONFIGURATION,
                              self._add_custom_configuration_to_archive)
        self._add_att_handler(model_constants.COHERENCE_CACHE_CONFIG_FILE, self._add_cache_config)
        self._add_att_handler(model_constants.COHERENCE_ACTIVE_DIRECTORY, self._add_active_directory)
        self._add_att_handler(model_constants.COHERENCE_SNAPSHOT_DIRECTORY, self._add_snapshot_directory)
        self._add_att_handler(model_constants.COHERENCE_TRASH_DIRECTORY, self._add_trash_directory)

    def discover(self):
        """
        discover the global, resource group template and partition coherence resources.
        :return: model name for coherence cluster:resources dictionary containing discovered coherence clusters
        """
        _method_name = 'discover'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        _logger.fine('WLSDPLY-06310', class_name=_class_name, method_name=_method_name)
        model_top_folder_name, result = self.get_coherence_clusters()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_top_folder_name, result)

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, self._dictionary

    def get_coherence_clusters(self):
        """
        Discover the Coherence clusters and archive the necessary coherence artifacts.
        :return: model folder name: dictionary with the discovered coherence clusters
        """
        _method_name = '_get_coherence_clusters'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.COHERENCE_CLUSTER_SYSTEM_RESOURCE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        coherence_clusters = self._find_names_in_folder(location)
        if coherence_clusters is not None:
            _logger.info('WLSDPLY-06311', len(coherence_clusters), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for coherence_cluster in coherence_clusters:
                _logger.info('WLSDPLY-06312', coherence_cluster, class_name=_class_name, method_name=_method_name)
                location.add_name_token(name_token, coherence_cluster)
                result[coherence_cluster] = OrderedDict()
                self._populate_model_parameters(result[coherence_cluster], location)
                model_subfolder_name, subfolder_result = self.get_coherence_cache_config(location)
                discoverer.add_to_model_if_not_empty(result[coherence_cluster], model_subfolder_name, subfolder_result)
                model_subfolder_name, subfolder_result = self.get_coherence_resource(location)
                discoverer.add_to_model_if_not_empty(result[coherence_cluster], model_subfolder_name, subfolder_result)
                location.remove_name_token(name_token)

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    #  private methods

    def get_coherence_cache_config(self, location):
        """
        Discover the coherence cache config for the coherence cluster. Add coherence cluster cache config to
        archive file.
        :param location: containing current context information for the location
        :return: model name for the coherence cache config: resource dictionary containing the discovered cache config
        """
        _method_name = '_get_coherence_cache_config'
        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.COHERENCE_CACHE_CONFIG
        location.append_location(model_top_folder_name)
        cache_configs = self._find_names_in_folder(location)
        if cache_configs is not None:
            name_token = self._alias_helper.get_name_token(location)
            for cache_config in cache_configs:
                _logger.fine('WLSDPLY-06313', cache_config, self._alias_helper.get_model_folder_path(location),
                             class_name=_class_name, method_name=_method_name)
                location.add_name_token(name_token, cache_config)
                result[cache_config] = OrderedDict()
                self._populate_model_parameters(result[cache_config], location)
                self._discover_subfolders(result[cache_config], location)
                location.remove_name_token(name_token)
        location.pop_location()
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    def get_coherence_resource(self, location):
        """
        Discover the coherence resources for the domain. Collect custom configuration files and persistence
        directories into the archive file.
        :param location: context containing the current location information
        :return: model name for coherence resource: dictionary containing coherence resources.
        """
        _method_name = '_get_coherence_resource'
        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.COHERENCE_RESOURCE
        location.append_location(model_top_folder_name)
        self._populate_model_parameters(result, location)
        self._discover_subfolders(result, location)
        location.pop_location()
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    # Private methods

    def _add_custom_configuration_to_archive(self, model_name, model_value, location):
        """
        Add custom configuration file to the archive. Modify the configuration file name in the model.
        :param model_name: attribute name of the custom configuration
        :param model_value: value containing the custom configuration file name
        :param location: context containing current location information
        :return: update custom configuration file name
        """
        _method_name = '_add_custom_configuration_to_archive'
        temp = LocationContext()
        temp.append_location(model_constants.COHERENCE_CLUSTER_SYSTEM_RESOURCE)
        cluster_name = location.get_name_for_token(self._alias_helper.get_name_token(temp))
        _logger.entering(cluster_name, model_name, model_value, class_name=_class_name, method_name=_method_name)
        new_name = model_value
        if model_value is not None:
            archive_file = self._model_context.get_archive_file()
            config_file = None
            try:
                config_file = FileUtils.getCanonicalFile(File(model_value))
            except (IOException, SecurityException), se:
                _logger.warning('WLSDPLY-06314', cluster_name, model_value, se.getLocalizedMessage(),
                                class_name=_class_name, method_name=_method_name)
                new_name = None

            if file is not None:
                try:
                    new_name = archive_file.addCoherenceConfigFile(cluster_name, config_file)
                    _logger.finer('WLSDPLY-06315', model_value, class_name=_class_name, method_name=_method_name)
                except (IllegalArgumentException, WLSDeployArchiveIOException), wioe:
                    _logger.warning('WLSDPLY-06316', cluster_name, model_value, wioe.getLocalizedMessage(),
                                    class_name=_class_name, method_name=_method_name)
                    new_name = None

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=new_name)
        return new_name

    def _add_cache_config(self, model_name, model_value, location):
        """
        Add the cache configuration file to the archive file. The file name stored in the cache configuration file
        attribute may be either a URL where the configuration is hosted or a physical location on the current machine.
        The file will be collected from either location and stored in the archive file. The attribute value will be
        updated to point to the location where the file will exist after the archive file is deployed.
        :param model_name: name of the coherence cluster cache config file attribute
        :param model_value: containing the cache configuration file URL or location
        :return: update cache configuration file value
        """
        _method_name = '_add_cache_config'
        temp = LocationContext()
        temp.append_location(model_constants.COHERENCE_CLUSTER_SYSTEM_RESOURCE)
        cluster_name = location.get_name_for_token(self._alias_helper.get_name_token(temp))
        _logger.entering(cluster_name, model_name, model_value, class_name=_class_name, method_name=_method_name)
        new_name = model_value
        if model_value is not None:
            archive_file = self._model_context.get_archive_file()
            success, url = _get_from_url(cluster_name, model_value)
            if success:
                if url is not None:
                    try:
                        new_name = archive_file.addCoherenceConfigFileFromUrl(cluster_name, url)
                        _logger.info('WLSDPLY-06317', cluster_name, url, new_name, class_name=_class_name,
                                     method_name=_method_name)
                    except (IllegalArgumentException, WLSDeployArchiveIOException), wioe:
                        _logger.warning('WLSDPLY-06318', cluster_name, model_value, 'url', wioe.getLocalizedMessage(),
                                        class_name=_class_name, method_name=_method_name)
                        new_name = None
                else:
                    try:
                        new_name = archive_file.addCoherenceConfigFile(cluster_name, File(model_value))
                        _logger.info('WLSDPLY-06319', cluster_name, model_value, new_name, class_name=_class_name,
                                     method_name=_method_name)
                    except (IllegalArgumentException, WLSDeployArchiveIOException), wioe:
                        _logger.warning('WLSDPLY-06318', cluster_name, model_value, 'file', wioe.getLocalizedMessage())
                        new_name = None

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=new_name)
        return new_name

    def _add_active_directory(self, model_name, model_value, location):
        return self._add_persistence_directory(model_name, model_value, location, 'active')

    def _add_snapshot_directory(self, model_name, model_value, location):
        return self._add_persistence_directory(model_name, model_value, location, 'snapshot')

    def _add_trash_directory(self, model_name, model_value, location):
        return self._add_persistence_directory(model_name, model_value, location, 'trash')

    def _add_persistence_directory(self, model_name, model_value, location, dir_type):
        """
        Add a directory to the archive file for the type of persistence directory. Return the updated location
        of the directory after deployment of the archive file.
        :param model_name: model name for the persistence directory attribute
        :param model_value: value of the current persistence directory location
        :param location: context containing current location information
        :param dir_type: type of persistence directory used to create the new directory name in the archive
        :return: updated model value for the new persistence directory location
        """
        _method_name = '_add_persistence_directory'
        temp = LocationContext()
        temp.append_location(model_constants.COHERENCE_CLUSTER_SYSTEM_RESOURCE)
        cluster_name = location.get_name_for_token(self._alias_helper.get_name_token(temp))
        _logger.entering(cluster_name, model_name, model_value, class_name=_class_name, method_name=_method_name)
        new_name = model_value
        if model_value is not None:
            archive_file = self._model_context.get_archive_file()
            try:
                new_name = archive_file.addCoherencePersistenceDirectory(cluster_name, dir_type)
                _logger.info('WLSDPLY-06320', cluster_name, model_value, dir_type, class_name=_class_name,
                             method_name=_method_name)
            except WLSDeployArchiveIOException, wioe:
                _logger.warning('WLSDPLY-06318', cluster_name, model_value, dir_type, wioe.getLocalizedMessage(),
                                class_name=_class_name, method_name=_method_name)
                new_name = None

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=new_name)
        return new_name


def _get_from_url(cluster_name, file_name):
    """
    Determine if the provided file name is a URL location where the file is hosted. If it is a URL, return
    a URL stream that can be used to retrieve the file from the hosted location.
    :param cluster_name: of the coherence cluster being discovered
    :param file_name: of the file to be tested as a URL
    :return: True if the file is hosted at a URL: URL file handle for the archive file to retrieve the file
    """
    url = None
    try:
        uri = URI(file_name)
        if 'http' == uri.getScheme():
            url = uri.toURL()
    except (URISyntaxException, MalformedURLException), e:
        _logger.warning('WLSDPLY-06321', cluster_name, file_name, e.getLocalizedMessage)
        return False, None

    return True, url
